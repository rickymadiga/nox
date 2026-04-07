# orchestrator/memory.py — NOX SHARED MEMORY (LIGHTWEIGHT)

import time
from typing import Dict, Any


class Memory:
    """
    Shared system memory for NOX.

    ✔ Lightweight (in-memory)
    ✔ Safe (won’t break Lily)
    ✔ Expandable (Redis/DB later)
    """

    def __init__(self):
        # 🔥 Per-user memory
        self.user_memory: Dict[str, Dict[str, Any]] = {}

        # 🔥 Global system memory
        self.global_memory: Dict[str, Any] = {}

    # =========================================================
    # USER MEMORY
    # =========================================================
    def get_user(self, user_id: str) -> Dict[str, Any]:
        if user_id not in self.user_memory:
            self.user_memory[user_id] = {
                "created_at": time.time(),
                "last_seen": time.time(),
                "data": {}
            }

        self.user_memory[user_id]["last_seen"] = time.time()
        return self.user_memory[user_id]["data"]

    def set_user_value(self, user_id: str, key: str, value: Any):
        user = self.get_user(user_id)
        user[key] = value

    def get_user_value(self, user_id: str, key: str, default=None):
        user = self.get_user(user_id)
        return user.get(key, default)

    def append_user_list(self, user_id: str, key: str, value: Any):
        user = self.get_user(user_id)

        if key not in user:
            user[key] = []

        if value not in user[key]:
            user[key].append(value)

    # =========================================================
    # GLOBAL MEMORY
    # =========================================================
    def set_global(self, key: str, value: Any):
        self.global_memory[key] = value

    def get_global(self, key: str, default=None):
        return self.global_memory.get(key, default)

    # =========================================================
    # DEBUG
    # =========================================================
    def dump(self) -> Dict[str, Any]:
        return {
            "users": self.user_memory,
            "global": self.global_memory
        }