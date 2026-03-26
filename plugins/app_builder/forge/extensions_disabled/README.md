# extensions/

This folder contains optional / experimental agents, hooks and capabilities
that can be plugged into the main Forge pipeline without touching core/.

Agents here should:
- be toggle-able (via config, CLI flag, env var)
- never be required for the basic happy path
- have clear activation points (before planner, after tester, etc.)

Planned first citizens:
- artifact_agent.py
- executor_agent.py
- evaluator_agent.py
- solution_archive_agent.py