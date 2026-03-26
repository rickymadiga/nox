# nox/core/websockets.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set
import json

router = APIRouter()

active_dashboards: Set[WebSocket] = set()


async def broadcast(message: str):
    """Send message to all dashboards"""

    dead = []

    for ws in active_dashboards:
        try:
            await ws.send_text(message)
        except Exception:
            dead.append(ws)

    for ws in dead:
        active_dashboards.discard(ws)


@router.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):

    print("[WS] HANDSHAKE ATTEMPT – accepted")
    await websocket.accept()

    active_dashboards.add(websocket)
    print(f"[WS] Dashboard connected — active: {len(active_dashboards)}")

    try:
        while True:

            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
            except Exception:
                data = {"type": "raw", "content": raw}

            print(f"[WS] Parsed message: {data}")

            # Echo test
            await websocket.send_json({
                "type": "debug",
                "received": data
            })

    except WebSocketDisconnect:

        active_dashboards.discard(websocket)
        print(f"[WS] Dashboard disconnected — active: {len(active_dashboards)}")

    except Exception as e:

        print(f"[WS] Unexpected error: {type(e).__name__} {e}")