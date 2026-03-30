import asyncio
from typing import Final

from ..core.event_bus import EventBus

# Agents
from ..agents.planner import PlannerAgent
from ..agents.coder import Coder
from ..agents.tester import Tester
from ..agents.reviewer import Reviewer
from ..agents.debugger import Debugger
from ..agents.fixer import Fixer
from ..agents.assembler import Assembler


AGENTS = [
    (PlannerAgent, "planner"),
    (Coder, "coder"),
    (Tester, "tester"),
    (Reviewer, "reviewer"),
    (Debugger, "debugger"),
    (Fixer, "fixer"),
    (Assembler, "assembler"),
]

INITIAL_WAIT_AFTER_TASK: Final[float] = 8.0


# 🔥 CLEAN RUNTIME (NO MAGIC)
class Runtime:
    def __init__(self, bus):
        self.bus = bus
        self.agents = {}

    def register_agent(self, name: str, agent):
        self.agents[name] = agent
        print(f"[Runtime] Registered agent: {name}")

    def get_agent(self, name: str):
        return self.agents.get(name)


# ─────────────────────────────────────────────
async def create_and_register_agents(runtime: Runtime):
    print("[Arena] Creating and registering agents...\n")

    runtime.agents.clear()

    for agent_class, name in AGENTS:
        try:
            # 🔥 NEW STANDARD
            agent = agent_class(runtime.bus, runtime)

            runtime.register_agent(name, agent)

            if hasattr(agent, "register"):
                agent.register()

            print(f"[Arena] {name} registered")

        except Exception as e:
            print(f"[Arena] Failed to register {name}: {e}")

    print("\n[Arena] All agents registered.\n")


# ─────────────────────────────────────────────
async def run_task_pipeline(runtime: Runtime, task: str):
    print(f"[Arena] → Publishing task: '{task}'")

    # 🔥 DICT EVENT (NOT Message)
    await runtime.bus.publish({
        "type": "TASK_REQUEST",
        "sender": "arena",
        "payload": {
            "task": task.strip(),
            "user_id": "default_user"
        }
    })

    print(f"[Arena] Waiting {INITIAL_WAIT_AFTER_TASK:.1f}s...\n")
    await asyncio.sleep(INITIAL_WAIT_AFTER_TASK)

    print("[Arena] Pipeline cycle finished.\n")


# ─────────────────────────────────────────────
async def run_forge(task: str):
    print("[EventBus] Initialized")

    bus = EventBus()

    runtime = Runtime(bus)

    # 🔥 Register agents
    await create_and_register_agents(runtime)

    # 🔥 Run pipeline
    await run_task_pipeline(runtime, task)

    return {
        "status": "completed",
        "task": task,
    }