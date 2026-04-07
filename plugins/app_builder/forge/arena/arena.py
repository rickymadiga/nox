import asyncio
import sys
from typing import Final

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


async def create_and_register_agents(bus: EventBus, context: dict) -> None:
    print("[Arena] Creating and registering agents...\n")

    context["agents"] = []

    # ✅ helper to access agents globally
    def get_agent(name):
        for a in context["agents"]:
            if a.name == name:
                return a
        return None

    context["get_agent"] = get_agent

    for agent_class, name in AGENTS:

        agent = agent_class(name, bus, context)

        # ✅ inject runtime
        agent.runtime = context

        agent.register()

        context["agents"].append(agent)

        print(f"[Arena] {name.capitalize()} registered")

    print("\n[Arena] All agents registered successfully.\n")


async def run_task_pipeline(bus: EventBus, task: str) -> None:

    message = Message(
        sender="arena",
        recipient="planner",
        message_type="TASK_REQUEST",
        payload={"task": task.strip()},
    )

    print(f"[Arena] → Publishing task: {task!r}")

    await bus.publish(message)

    print(f"[Arena] Waiting {INITIAL_WAIT_AFTER_TASK:.1f}s...\n")

    await asyncio.sleep(INITIAL_WAIT_AFTER_TASK)

    print("[Arena] Pipeline cycle finished.\n")


async def run_forge(task: str, runtime=None, user_id: str = "default_user"):

    # 🔥 reuse runtime bus if available
    if runtime and hasattr(runtime, "bus"):
        bus = runtime.bus
    else:
        bus = EventBus()
        bus.message_class = Message

    # 🔥 shared context
    context = {
        "bus": bus,
        "runtime": runtime,
        "user_id": user_id
    }

    # memory
    memory = Memory("memory", bus, context)
    context["memory"] = memory

    await create_and_register_agents(bus, context)

    # 🔥 RESULT HOLDER
    result_container = {"result": None}

    # 🔥 LISTENER FOR COMPLETION
    async def on_complete(message: Message):
        print("[Arena] ✅ forge_complete received")

        result_container["result"] = message.payload

    bus.subscribe("forge_complete", on_complete)

    # 🔥 START PIPELINE
    await bus.publish(
        Message(
            sender="arena",
            recipient="planner",
            message_type="TASK_REQUEST",
            payload={
                "task": str(task).strip() if task else "",
                "user_id": user_id
            },
        )
    )

    print(f"[Arena] Waiting for completion...\n")

    # 🔥 WAIT UNTIL RESULT OR TIMEOUT
    for _ in range(20):  # ~20 seconds max
        if result_container["result"] is not None:
            break
        await asyncio.sleep(1)

    print("[Arena] Pipeline cycle finished.\n")

    # 🔥 RETURN REAL RESULT
    return result_container["result"] or {
        "status": "timeout",
        "task": task,
        "user_id": user_id
    }