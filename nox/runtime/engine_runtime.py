import asyncio
import logging
import json
from typing import Any, Dict, List, Optional, Callable
from collections import defaultdict

from nox.core.capability_index import CapabilityIndex
from nox.core.plugin_loader import load_plugins

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────
# SIMPLE EVENT BUS
# ────────────────────────────────────────────────
class SimpleBus:
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)

    def subscribe(self, event_type: str, callback: Callable) -> None:
        self.subscribers[event_type].append(callback)

    async def publish(self, message: Any) -> None:
        event_type = None

        if isinstance(message, dict):
            event_type = message.get("type") or message.get("message_type")
        elif hasattr(message, "message_type"):
            event_type = message.message_type

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
# RUNTIME
# ────────────────────────────────────────────────
class Runtime:
    def __init__(self):
        self.agents: Dict[str, Any] = {}
        self.capabilities = CapabilityIndex()
        self.bus = SimpleBus()

        logger.info("[RUNTIME] Initialized")

    def register_agent(self, name: str, agent: Any) -> None:
        try:
            if hasattr(agent, "runtime"):
                agent.runtime = self

            self.agents[name] = agent
            logger.info(f"[AGENT] Registered: {name}")

        except Exception as e:
            logger.error(f"[AGENT ERROR] register {name}: {e}")

    def get_agent(self, name: str) -> Optional[Any]:
        return self.agents.get(name)

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

            logger.info(f"[CAPABILITY] {agent_name} → {intent}")

        except Exception as e:
            logger.error(f"[CAPABILITY ERROR] {agent_name}: {e}")

    async def execute_agents(
        self,
        agent_names: List[str],
        task: Dict[str, Any]
    ) -> Dict[str, Any]:
        if isinstance(task, str):
            task = {"prompt": task}

        async def run_single(name: str):
            agent = self.get_agent(name)
            if not agent:
                return name, {"error": "agent not found"}

            try:
                print(f"[RUNTIME] → Executing {name}")

                result = agent.run(task)
                if asyncio.iscoroutine(result):
                    result = await result

                return name, result

            except Exception as e:
                logger.error(f"[AGENT ERROR] {name}: {e}", exc_info=True)
                return name, {"error": str(e)}

        coros = [run_single(name) for name in agent_names]
        responses = await asyncio.gather(*coros, return_exceptions=True)

        results = {}
        for item in responses:
            if isinstance(item, Exception):
                continue
            name, res = item
            results[name] = res

        return results


# ────────────────────────────────────────────────
# ENGINE (LILY-FIRST + BILLING + MONETIZATION)
# ────────────────────────────────────────────────
class Engine:
    def __init__(self):
        self.runtime = Runtime()

        # Load plugins (Lily, billing_agent, monetization_agent, stripe_agent, etc.)
        load_plugins(self.runtime)

        logger.info("[ENGINE] Ready")

    def _synthesize(self, results: Dict[str, Any]) -> str:
        """Simple synthesis helper"""
        if not results:
            return "No output."

        messages = []
        for agent, res in results.items():
            if isinstance(res, dict):
                if "message" in res:
                    messages.append(res["message"])
                elif "response" in res:
                    messages.append(res["response"])
                elif "output" in res:
                    messages.append(res["output"])
                else:
                    messages.append(f"{agent}: {str(res)}")
            else:
                messages.append(f"{agent}: {str(res)}")

        return "\n\n".join(messages)

    async def handle_prompt(self, prompt: str) -> Dict[str, Any]:
        if not prompt.strip():
            return {"status": "error", "response": "Empty prompt"}

        task = {
            "prompt": prompt,
            "intent": "user_prompt",
            "user_id": "default_user"
        }

        lily = self.runtime.get_agent("lily")
        billing = self.runtime.get_agent("billing_agent")
        monetizer = self.runtime.get_agent("monetization_agent")

        if not lily:
            return {"status": "error", "response": "Lily not available"}

        try:
            # =========================
            # 1. LILY DECIDES
            # =========================
            lily_res = lily.run(task)
            if asyncio.iscoroutine(lily_res):
                lily_res = await lily_res

            if not isinstance(lily_res, dict):
                return {
                    "status": "success",
                    "response": str(lily_res)
                }

            action = lily_res.get("action", "respond")

            # =========================
            # 2. BILLING CHECK
            # =========================
            cost = 0
            if billing:
                bill_res = billing.run({
                    "user_id": task["user_id"],
                    "action": action
                })

                if isinstance(bill_res, dict) and bill_res.get("status") == "blocked":
                    upsell_msg = None
                    trigger = None

                    if monetizer:
                        upsell = monetizer.run({
                            "user_id": task["user_id"],
                            "action": action,
                            "success": False
                        })

                        if isinstance(upsell, dict) and upsell.get("upsell"):
                            upsell_msg = upsell.get("message")
                            trigger = upsell.get("trigger")

                    return {
                        "status": "error",
                        "response": bill_res.get("message", "Not enough credits"),
                        "upsell": upsell_msg,
                        "trigger": trigger
                    }

                cost = bill_res.get("cost", 0) if isinstance(bill_res, dict) else 0

            # =========================
            # 3. EXECUTE ACTION
            # =========================
            results = None

            if action == "respond":
                final_response = lily_res.get("message") or "Done."

            elif action == "delegate":
                target = lily_res.get("target")
                if not target:
                    return {"status": "error", "response": "No target specified"}

                results = await self.runtime.execute_agents([target], task)
                final_response = self._synthesize(results)

            elif action == "delegate_multi":
                targets = lily_res.get("targets", [])
                if not targets:
                    return {"status": "error", "response": "No targets provided"}

                print(f"[ENGINE] Multi-delegation → {targets}")
                results = await self.runtime.execute_agents(targets, task)
                final_response = self._synthesize(results)

            elif action == "orchestrate":
                agents = self.runtime.capabilities.match(prompt)
                if not agents:
                    return {
                        "status": "success",
                        "response": "No suitable agent found."
                    }

                results = await self.runtime.execute_agents(agents, task)
                final_response = self._synthesize(results)

            else:
                final_response = lily_res.get("message", "Done.")

            # =========================
            # 4. AUTO RECHARGE CHECK (Your new block)
            # =========================
            if billing:
                # Check low credits and trigger auto-recharge if enabled
                user = billing._get_user(task["user_id"])  # direct access for simplicity
                if user["credits"] < 5 and user.get("auto_recharge"):
                    stripe_agent = self.runtime.get_agent("stripe_agent")
                    if stripe_agent:
                        try:
                            # Stripe SetupIntent / auto charge
                            stripe_agent.auto_charge(user_id=task["user_id"], amount=500)
                            billing.add_credits(task["user_id"], 100)  # example amount
                            print(f"[AUTO-RECHARGE] Triggered for user {task['user_id']}")
                        except Exception as e:
                            print(f"[AUTO-RECHARGE FAILED] {e}")

            # =========================
            # 5. MONETIZATION (SUCCESS)
            # =========================
            upsell_msg = None
            trigger = None

            if monetizer:
                upsell = monetizer.run({
                    "user_id": task["user_id"],
                    "action": action,
                    "success": True
                })

                if isinstance(upsell, dict) and upsell.get("upsell"):
                    upsell_msg = upsell.get("message")
                    trigger = upsell.get("trigger")

            # =========================
            # FINAL RESPONSE
            # =========================
            return {
                "status": "success",
                "response": final_response,
                "upsell": upsell_msg,
                "trigger": trigger,
                "results": results
            }

        except Exception as e:
            logger.error(f"[ENGINE ERROR] {e}", exc_info=True)
            return {
                "status": "error",
                "response": f"Internal error: {str(e)}"
            }


# ────────────────────────────────────────────────
# GLOBAL ENGINE INSTANCE
# ────────────────────────────────────────────────
engine = Engine()