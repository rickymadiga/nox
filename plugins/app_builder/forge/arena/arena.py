import asyncio
from typing import Final, List

from ..core.event_bus import EventBus
from ..core.message import Message
from ..memory.memory import Memory

from ..agents.planner import PlannerAgent
from ..agents.coder import Coder
from ..agents.tester import Tester
from ..agents.reviewer import Reviewer
from ..agents.debugger import Debugger
from ..agents.assembler import Assembler
from ..agents.fixer import Fixer


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


# ✅ CLEAN RUNTIME OBJECT (fixes ALL your errors)
class Runtime:
    def __init__(self, bus):
        self.bus = bus
        self.agents = []
        self.memory = None

    def get_agent(self, name):
        for a in self.agents:
            if a.name == name:
                return a
            return None


async def create_and_register_agents(runtime: Runtime) -> None:
    print("[Arena] Creating and registering agents...\n")

    for agent_class, name in AGENTS:
        agent = agent_class(name, runtime.bus, runtime)
        agent.runtime = runtime

        agent.runtime = runtime  # ✅ consistent runtime injection
        agent.register()

        runtime.agents.append(agent)

        print(f"[Arena] {name.capitalize()} registered")

    print("\n[Arena] All agents registered successfully.\n")


async def run_task_pipeline(runtime: Runtime, task: str) -> None:

    message = Message(
        sender="arena",
        recipient="planner",
        message_type="TASK_REQUEST",
        payload={"task": task.strip()},
    )

    print(f"[Arena] → Publishing task: {task!r}")

    await runtime.bus.publish(message)

    print(f"[Arena] Waiting {INITIAL_WAIT_AFTER_TASK:.1f}s...\n")

    await asyncio.sleep(INITIAL_WAIT_AFTER_TASK)

    print("[Arena] Pipeline cycle finished.\n")


async def run_forge(task: str):

    bus = EventBus()
    bus.message_class = Message

    runtime = Runtime(bus)

    # ✅ memory attached to runtime
    memory = Memory("memory", bus, runtime)
    runtime.memory = memory

    await create_and_register_agents(runtime)

    await run_task_pipeline(runtime, task)

    return {
        "status": "completed",
        "task": task,
    }