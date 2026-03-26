# nox/core/routes.py
"""
Test endpoints and WebSocket routes for development and debugging.
"""

from fastapi import (
    APIRouter,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    Request,
)
from typing import Dict, Any
import json

from nox.utils.logger import logger

print(">>> ROUTES.PY LOADED - ENGINE DISPATCH VERSION <<<")

# ────────────────────────────────────────────────
# HTTP Router
# ────────────────────────────────────────────────

router = APIRouter(prefix="/test", tags=["test", "dev"])


@router.post("/content")
async def test_generate_content(
    payload: Dict[str, Any],
    request: Request,
):
    """
    Test endpoint to trigger the content generator agent
    directly (useful for debugging plugins).
    """

    registry = request.app.state.registry
    agent = registry.get("content_generator")

    if not agent:
        raise HTTPException(
            status_code=500,
            detail="ContentGeneratorAgent not registered",
        )

    logger.info("[TEST] Direct content_generator call")

    result = await agent.process(payload)

    return result


# ────────────────────────────────────────────────
# WebSocket Router
# ────────────────────────────────────────────────

ws_router = APIRouter(tags=["websocket"])

active_connections: set[WebSocket] = set()


@ws_router.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):

    logger.info("[WS] HANDSHAKE ATTEMPT")

    try:
        await websocket.accept()

        logger.info("[WS] Connection accepted")

        active_connections.add(websocket)

        logger.info(
            f"[WS] Dashboard connected — active: {len(active_connections)}"
        )

        await websocket.send_json({
            "type": "system",
            "message": "connected:dashboard"
        })

        # ────────────────────────────────────────────────
        # MESSAGE LOOP
        # ────────────────────────────────────────────────

        while True:

            raw_data = await websocket.receive_text()

            logger.info(f"[WS → raw] {raw_data}")

            try:
                data = json.loads(raw_data)

                logger.info(f"[WS → parsed] {data}")

                msg_type = data.get("type")
                content = data.get("content", "").strip()

                # ────────────────────────────────────────────────
                # Engine Dispatch (CORRECT ARCHITECTURE)
                # ────────────────────────────────────────────────

                if msg_type == "message" and content:

                    engine = websocket.app.state.engine

                    logger.info(
                        f"[WS] Dispatching prompt to engine: {content[:60]}..."
                    )

                    result = await engine.handle_prompt(content)

                    await websocket.send_json({
                        "type": "task_result",
                        "message": result.get("message", str(result))
                    })


                    logger.info("[WS] Engine returned result")

                # ────────────────────────────────────────────────
                # Ping/Pong
                # ────────────────────────────────────────────────

                elif msg_type == "ping":

                    await websocket.send_json({"type": "pong"})

                # ────────────────────────────────────────────────
                # Echo fallback
                # ────────────────────────────────────────────────

                else:

                    await websocket.send_json({
                        "type": "echo",
                        "original": data,
                    })

            except json.JSONDecodeError:

                logger.warning("[WS] Received non-JSON message")

                await websocket.send_text(f"echo: {raw_data}")

    except WebSocketDisconnect:

        active_connections.discard(websocket)

        logger.info(
            f"[WS] Dashboard disconnected — active: {len(active_connections)}"
        )

    except Exception as e:

        logger.error(
            f"[WS ERROR] {type(e).__name__}: {e}",
            exc_info=True,
        )

        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Server error: {str(e)}",
            })

            await websocket.close(code=1011)

        except Exception:
            pass

    finally:

        active_connections.discard(websocket)