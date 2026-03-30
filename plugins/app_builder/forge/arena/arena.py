import asyncio
from typing import Final

from ..core.event_bus import EventBus
from ..core.message import Message
from ..memory.memory import Memory

# Import your agents (updated class names where needed)
from ..agents.planner import PlannerAgent
from ..agents.coder import Coder          # assuming class is Coder
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


# ✅ Updated Runtime with register_agent support
class Runtime:
    def __init__(self, bus):
        self.bus = bus
        self.agents: dict = {}       # Now using dict for faster lookup
        self.memory = None

    def register_agent(self, name: str, agent: any) -> None:
        """Register agent properly"""
        if hasattr(agent, "runtime"):
            agent.runtime = self
        self.agents[name] = agent
        print(f"[Runtime] Registered agent: {name}")

    def get_agent(self, name: str):
        """Get agent by name"""
        return self.agents.get(name)

    def get_all_agents(self):
        return self.agents


async def create_and_register_agents(runtime: Runtime) -> None:
    """Create and register all agents using the new style"""
    print("[Arena] Creating and registering agents...\n")

    # Clear previous agents if any
    runtime.agents.clear()

    for agent_class, name in AGENTS:
        try:
            # 🔥 New way: pass runtime directly to agent constructor
            agent = agent_class(runtime)          # This matches your requested style

            # Register using the proper method
            runtime.register_agent(name, agent)

            # Also call agent's register() if it exists
            if hasattr(agent, "register") and callable(agent.register):
                agent.register()

            print(f"[Arena] {name.capitalize()} registered successfully")

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

    # Register all agents using the new method
    await create_and_register_agents(runtime)

    # Run the actual task pipeline
    await run_task_pipeline(runtime, task)

    return {
        "status": "completed",
        "task": task,
    }