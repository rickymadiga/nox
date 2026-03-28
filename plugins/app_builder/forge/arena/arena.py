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


# ────────────────────────────────────────────────
# CREATE + REGISTER AGENTS
# ────────────────────────────────────────────────
async def create_and_register_agents(bus: EventBus, context: dict, runtime=None) -> None:
    print("[Arena] Creating and registering agents...\n")

    context["agents"] = []

    # helper
    def get_agent(name):
        for a in context["agents"]:
            if a.name == name:
                return a
        return None

    context["get_agent"] = get_agent

    for agent_class, name in AGENTS:
        agent = agent_class(name, bus, context)

        # ✅ FIXED: separate runtime + context
        agent.runtime = runtime
        agent.context = context

        agent.register()
        context["agents"].append(agent)

        print(f"[Arena] {name.capitalize()} registered")

    print("\n[Arena] All agents registered successfully.\n")


# ────────────────────────────────────────────────
# RUN TASK PIPELINE
# ────────────────────────────────────────────────
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


# ────────────────────────────────────────────────
# MAIN FORGE ENTRY
# ────────────────────────────────────────────────
async def run_forge(task: str, runtime=None):

    bus = EventBus()
    bus.message_class = Message

    # ✅ FIXED context (no syntax bug, no misuse)
    context = {
        "bus": bus,
        "runtime": runtime
    }

    # memory
    memory = Memory("memory", bus, context)
    context["memory"] = memory

    # register agents
    await create_and_register_agents(bus, context, runtime)

    # ────────────────────────────────────────────
    # RESULT COLLECTION (EVENT-BASED)
    # ────────────────────────────────────────────
    results = {}
    logs = []

    def on_update(message):
        msg = message.get("message") if isinstance(message, dict) else str(message)
        print(f"[UPDATE] {msg}")
        logs.append(msg)

    def on_complete(message):
        print(f"[COMPLETE] {message}")
        results["final"] = message

    bus.subscribe("TASK_UPDATE", on_update)
    bus.subscribe("TASK_COMPLETE", on_complete)

    # run pipeline
    await run_task_pipeline(bus, task)

    # ────────────────────────────────────────────
    # COLLECT STREAM LOGS FROM AGENTS (QUEUES)
    # ────────────────────────────────────────────
    for _ in range(20):  # polling loop
        for agent in context["agents"]:
            queues = getattr(agent, "queues", None)

            if queues:
                q = queues.get("default_user")
                if q:
                    try:
                        while not q.empty():
                            msg = q.get_nowait()
                            logs.append(msg)
                    except Exception:
                        pass

        await asyncio.sleep(0.3)

    return {
        "status": "completed",
        "task": task,
        "logs": logs,
        "result": results.get("final")
    }