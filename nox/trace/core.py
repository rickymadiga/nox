# trace/core.py

import time
import uuid


class TraceManager:
    ENABLED = True
    SLOW_THRESHOLD_MS = 10

    def __init__(self, expected=None):
        if not self.ENABLED:
            return

        self.trace_id = f"trace-{uuid.uuid4().hex[:8]}"
        self.expected = expected or []

        self.started_at = time.perf_counter()
        self.last_checkpoint = self.started_at

        self.stages = []
        self.timings = {}
        self.status = "running"

    # ─────────────────────────────
    def stage(self, name: str):
        if not self.ENABLED:
            return

        now = time.perf_counter()
        delta = (now - self.last_checkpoint) * 1000

        self.stages.append(name)
        self.timings[name] = round(delta, 3)

        self.last_checkpoint = now

    # ─────────────────────────────
    def finish(self):
        if not self.ENABLED:
            return

        total = (time.perf_counter() - self.started_at) * 1000
        total = round(total, 3)

        missing = set(self.expected) - set(self.stages)

        print("\n" + "=" * 50)
        print("⏱ TRACE REPORT")
        print(f"Trace ID: {self.trace_id}\n")

        for stage, t in self.timings.items():
            slow = " ⚠" if t > self.SLOW_THRESHOLD_MS else ""
            print(f"{stage:<20} → {t}ms{slow}")

        print(f"\nTotal Time{'':<10} → {total}ms")

        if missing:
            print("\n🚨 PIPE BREAK DETECTED")
            print(f"Missing: {list(missing)}")

        print("=" * 50 + "\n")

    # ─────────────────────────────
    def attach(self, task: dict):
        if not self.ENABLED:
            return task

        task["_trace"] = self
        return task

    # ─────────────────────────────
    @staticmethod
    def get(task: dict):
        return task.get("_trace")