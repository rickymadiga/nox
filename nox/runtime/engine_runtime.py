import asyncio
import time
import logging
from typing import Any, Dict, List, Optional, Callable
from collections import defaultdict
from typing import Any, Optional

logger = logging.getLogger(__name__)
DEV_USERS = ["nox", "admin", "cosmic ethic"]
from ..core.capability_index import CapabilityIndex
from .plugin_loader import load_plugins

# ────────────────────────────────────────────────
# SIMPLE EVENT BUS
# ────────────────────────────────────────────────
class SimpleBus:
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)

    def subscribe(self, event_type: str, callback: Callable) -> None:
        self.subscribers[event_type].append(callback)
        logger.debug(f"[BUS] Subscribed to event: {event_type}")

    async def publish(self, message: Any) -> None:
        if isinstance(message, dict):
            event_type = message.get("type") or message.get("message_type")
        elif hasattr(message, "message_type"):
            event_type = message.message_type
        else:
            event_type = None

        if not event_type:
            return

        for callback in self.subscribers.get(event_type, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)
            except Exception as e:
                logger.error(f"[BUS ERROR] {event_type}: {e}", exc_info=True)


# ────────────────────────────────────────────────
# RUNTIME CORE
# ────────────────────────────────────────────────
class Runtime:
    def __init__(self, bus: Optional[SimpleBus] = None):
        self.bus = bus or SimpleBus()

        self.agents: Dict[str, Any] = {}
        self.system_agents: Dict[str, Any] = {}
        self.tools: Dict[str, Any] = {}

        self.capabilities = CapabilityIndex()

        # Multi-user support for last_zip
        self.last_zip: Dict[str, Dict[str, Any]] = {}   # user_id → zip_data
        self.logs: List[str] = []

        # Subscribe to forge completion event
        self.bus.subscribe("forge_complete", self._on_forge_complete)

        logger.info("[RUNTIME] Initialized successfully")

    # ───── TOOLS ─────
    def register_tool(self, name: str, tool: Any) -> None:
        self.tools[name] = tool
        logger.info(f"[TOOL] Registered: {name}")

    def get_tool(self, name: str) -> Optional[Any]:
        return self.tools.get(name)

    # ───── AGENTS ─────
    def register_agent(self, name: str, agent: Any) -> None:
        try:
            if hasattr(agent, "runtime"):
                agent.runtime = self
            self.agents[name] = agent
            logger.info(f"[AGENT] Registered: {name}")
        except Exception as e:
            logger.error(f"[AGENT ERROR] Failed to register {name}: {e}", exc_info=True)

    def register_system_agent(self, name: str, agent: Any) -> None:
        try:
            if hasattr(agent, "runtime"):
                agent.runtime = self
            self.system_agents[name] = agent
            logger.info(f"[SYSTEM AGENT] Registered: {name}")
        except Exception as e:
            logger.error(f"[SYSTEM AGENT ERROR] Failed to register {name}: {e}", exc_info=True)

    def get_agent(self, name: str) -> Optional[Any]:
        return self.agents.get(name) or self.system_agents.get(name)

    # ───── CAPABILITIES ─────
    def register_capability(
        self,
        agent_name: str,
        intent: str,
        keywords: List[str],
        priority: int = 0
    ) -> None:
        try:
            self.capabilities.register(
                agent_name=agent_name,
                intent=intent,
                keywords=keywords
            )
            if priority != 0:
                self.capabilities.set_priority(agent_name, priority)

            logger.info(f"[CAPABILITY] Registered → {agent_name} for intent: {intent}")
        except Exception as e:
            logger.error(f"[CAPABILITY ERROR] {agent_name}: {e}", exc_info=True)

    # ───── EXECUTION ─────
    async def execute_agent(self, name: str, task: Dict[str, Any]) -> Dict[str, Any]:
        agent = self.get_agent(name)
        if not agent:
            return {"error": f"Agent '{name}' not found"}

        try:
            result = agent.run(task)
            if asyncio.iscoroutine(result):
                result = await result
            return result or {}
        except Exception as e:
            logger.error(f"[AGENT EXECUTION ERROR] {name}: {e}", exc_info=True)
            return {"error": str(e)}

    # ───── FORGE COMPLETE HANDLER ─────
    async def _on_forge_complete(self, message: Any) -> None:
        try:
            payload = (
                message.payload
                if hasattr(message, "payload")
                else message.get("payload", {})
            )

            user_id = payload.get("user_id", "guest")
            zip_bytes = payload.get("zip_bytes")

            if zip_bytes:
                self.last_zip[user_id] = {
                    "bytes": zip_bytes,
                    "filename": payload.get("filename", "nox_app.zip")
                }

            log_msg = f"✅ Build completed for user '{user_id}' → {payload.get('project_name', 'Unnamed')}"
            self.logs.append(log_msg)

            logger.info(f"[RUNTIME] Forge complete processed for user: {user_id}")

            # Notify Lily if available
            lily = self.get_agent("lily")
            if lily and hasattr(lily, "complete_job"):
                lily.complete_job(user_id, self.last_zip.get(user_id, {}))

        except Exception as e:
            logger.error(f"[RUNTIME] Error in _on_forge_complete: {e}", exc_info=True)


# ────────────────────────────────────────────────
# ENGINE
# ────────────────────────────────────────────────


class Engine:
    MIN_BUILD_CREDITS = 200  # 🔒 hard minimum threshold

    def __init__(self):
        self.runtime = Runtime()
        self._billing_locks = defaultdict(asyncio.Lock)

        try:
            load_plugins(self.runtime)
            logger.info("[ENGINE] Plugins loaded successfully")
        except Exception as e:
            logger.error(f"[PLUGIN LOAD ERROR] {e}", exc_info=True)

        logger.info("[ENGINE] Initialized and ready")

    # ────────────────────────────────────────────────
    # EVENT EMITTER (Clean Async Version)
    # ────────────────────────────────────────────────
    async def emit(self, event_type: str, payload: dict = None):
        """Emit events to the internal bus"""
        try:
            from ..core.message import Message
            message = Message(
                message_type=event_type,
                payload=payload or {},
                sender="engine",
                recipient="all"
            )
            await self.runtime.bus.publish(message)
        except Exception as e:
            print(f"[ENGINE EMIT ERROR] {e}")

    # ────────────────────────────────────────────────
    # EXECUTE AGENT
    # ────────────────────────────────────────────────
    async def execute_agent(self, agent_name: str, task: Any, user_id: Optional[str] = None):
        try:
            # 🚫 Block direct build execution (security layer)
            if agent_name == "app_builder" and not task.get("authorized"):
                raise Exception("❌ Unauthorized build attempt")

            agent = self.runtime.get_agent(agent_name)
            if not agent:
                logger.warning(f"[Engine] Agent not found: {agent_name}")
                return {"error": "Agent not found"}

            logger.info(f"[Engine] Executing agent: {agent_name}")

            if hasattr(agent, "run"):
                if user_id is not None and isinstance(task, dict):
                    task = task.copy()
                    task["user_id"] = user_id

                result = agent.run(task)

                if asyncio.iscoroutine(result):
                    result = await result

                return result

            logger.warning(f"[Engine] Agent {agent_name} has no run() method")
            return {"error": "Agent has no run() method"}

        except Exception as e:
            logger.error(f"[Engine] Failed to execute {agent_name}: {e}", exc_info=True)
            return {"error": str(e)}

    # ────────────────────────────────────────────────
    # 🔥 PRE-AUTH BUILD FLOW - Updated
    # ────────────────────────────────────────────────
    async def _run_build_with_capture(self, task, user_id, cost):
        billing = self.runtime.get_agent("billing_agent")

        try:
            # ✅ mark authorized
            task["authorized"] = True

            await self.execute_agent("app_builder", task, user_id=user_id)

            # Skip capture for dev users
            if user_id not in DEV_USERS:
                billing.capture(user_id, cost)
                logger.info(f"[BILLING] Captured {cost} credits for {user_id}")
            else:
                logger.info(f"[BILLING] DEV user {user_id} - build completed FREE")

            # Optional: Emit success event
            self.emit("build_complete", {
                "user_id": user_id,
                "status": "success",
                "cost": cost,
                "dev_mode": user_id in DEV_USERS
            })

        except Exception as e:
            # ❌ FAIL → release (only for normal users)
            if user_id not in DEV_USERS:
                billing.release(user_id, cost)
                logger.error(f"[BILLING] Released {cost} credits for {user_id} due to error: {e}")
            else:
                logger.error(f"[BILLING] DEV user {user_id} build failed: {e}")

            # Optional: Emit failure event
            self.emit("build_failed", {
                "user_id": user_id,
                "error": str(e),
                "cost": cost
            })

    # ────────────────────────────────────────────────
    # HANDLE PROMPT (MAIN ENTRY) - Updated with DEV Support
    # ────────────────────────────────────────────────
    async def handle_prompt(self, prompt: str, user_id: str = "default_user"):
        start_time = time.time()

        try:
            # Early DEV check - skip everything for god mode
            is_dev = user_id in DEV_USERS

            lily = self.runtime.get_agent("lily")
            if not lily:
                return {"response": "❌ Lily agent not available"}

            decision = await lily.run({
                "prompt": prompt,
                "user_id": user_id,
                "context": {}
            })

            action = decision.get("action")
            message = decision.get("message", "")
            cost = decision.get("price", 0)

            # ───── QUOTE ─────
            if action == "quote":
                if is_dev:
                    return {
                        "response": f"{message}\n\n🔥 **GOD MODE**: This build is FREE for you.",
                        "price": 0,
                        "awaiting_confirmation": False
                    }
                return {
                    "response": message,
                    "price": cost,
                    "awaiting_confirmation": True
                }

            # ───── BUILD ─────
            if action == "build":
                billing = self.runtime.get_agent("billing_agent")
                if not billing:
                    return {"response": "❌ Billing system unavailable"}

                cost = max(self.MIN_BUILD_CREDITS, int(decision.get("price") or 0))
                prompt_str = str(decision.get("prompt", prompt))

                task = {
                    "prompt": prompt_str,
                    "input": prompt_str,
                    "user_id": user_id,
                    "context": decision.get("context") or {"user_id": user_id}
                }

                # 🔥 DEV USER SHORT-CIRCUIT
                if is_dev:
                    task["authorized"] = True
                    asyncio.create_task(
                        self.execute_agent("app_builder", task, user_id=user_id)
                    )

                    await self.emit("build_started", {   # ← Added await
                        "user_id": user_id,
                        "prompt": prompt_str,
                        "cost": 0,
                        "dev_mode": True
                    })

                    return {
                        "response": f"🚀 God Mode Build Started (FREE - Unlimited)",
                        "zip": None,
                        "logs": list(getattr(self.runtime, "logs", []))[-10:],
                        "graph": {
                            "status": "running",
                            "steps": ["Planner", "Coder", "Tester", "Reviewer", "Assembler"]
                        }
                    }

                # ───── NORMAL USER FLOW (original logic preserved) ─────
                lock = self._billing_locks[user_id]

                async with lock:
                    balance = billing.get_balance(user_id)
                    credits = balance["credits"]

                if credits < cost:
                    return {"response": f"❌ Not enough credits. Need {cost}, have {credits}."}

                reserve = billing.reserve(user_id, cost)

                # Start build in background
                asyncio.create_task(
                    self._run_build_with_capture(task, user_id, cost)
                )

                await self.emit("build_started", {   # ← Added await
                    "user_id": user_id,
                    "prompt": prompt_str,
                    "cost": cost
                })

                return {
                    "response": f"🚀 Build started ({cost} credits reserved)",
                    "zip": None,
                    "logs": list(getattr(self.runtime, "logs", []))[-10:],
                    "graph": {
                        "status": "running",
                        "steps": ["Planner", "Coder", "Tester", "Reviewer", "Assembler"]
                    }
                }

            # ───── DEFAULT CHAT ─────
            return {
                "response": message or "🤖 Done"
            }

        except Exception as e:
            logger.error(f"[ENGINE ERROR] {e}", exc_info=True)
            return {
                "response": f"❌ Error: {str(e)}"
            }

        finally:
            duration = time.time() - start_time
            logger.info(f"[ENGINE] Completed in {duration:.2f}s")
    
# ────────────────────────────────────────────────
# GLOBAL SINGLETON
# ────────────────────────────────────────────────
engine = Engine()