import asyncio
from typing import Final

from ..core.event_bus import EventBus
from ..core.message import Message
from ..memory.memory import Memory

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


# ✅ Clean Runtime
class Runtime:
    def __init__(self, bus):
        self.bus = bus
        self.agents = []
        self.memory = None

    def get_agent(self, name: str):
        for agent in self.agents:
            if getattr(agent, "name", None) == name:
                return agent
        return None


async def create_and_register_agents(runtime: Runtime) -> None:
    """Register all agents into the runtime"""
    print("[Arena] Creating and registering agents...\n")

    runtime.agents.clear()   # Clean slate

    for agent_class, name in AGENTS:
        try:
            agent = agent_class(name, runtime.bus, runtime)
            agent.runtime = runtime
            agent.register()

            runtime.agents.append(agent)
            print(f"[Arena] {name.capitalize()} registered")
        except Exception as e:
            print(f"[Arena] Failed to register {name}: {e}")

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

    print(f"[Arena] Waiting {INITIAL_WAIT_AFTER_TASK:.1f}s after task...\n")
    await asyncio.sleep(INITIAL_WAIT_AFTER_TASK)

    print("[Arena] Pipeline cycle finished.\n")


async def run_forge(task: str, runtime: Runtime | None = None):
    print("[EventBus] Initialized")

    bus = EventBus()
    bus.message_class = Message

    # Create runtime if not provided
    if runtime is None:
        runtime = Runtime(bus)

    runtime.bus = bus
    runtime.memory = Memory("memory", bus, runtime)

    # Register all agents
    await create_and_register_agents(runtime)

    # Run the actual task
    await run_task_pipeline(runtime, task)

    return {
        "status": "completed",
        "task": task,
    }