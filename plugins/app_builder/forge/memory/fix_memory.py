# forge/memory/fix_memory.py

from collections import defaultdict
import re

class FixMemory:
    """Improved self-learning memory for the Fixer agent"""

    def __init__(self):
        # pattern → list of (action, task, count)
        self.knowledge: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
        self.success_patterns = set()

    def record(self, pattern: str, action: str, task: str = ""):
        """Record a specific fix action for a pattern"""
        pattern = pattern.strip().lower()
        task = task.strip().lower()
        action = action.strip().lower()

        # Avoid duplicates
        for existing_action, existing_task, count in self.knowledge[pattern]:
            if existing_action == action and existing_task == task:
                # Increase confidence
                self.knowledge[pattern].remove((existing_action, existing_task, count))
                self.knowledge[pattern].append((existing_action, existing_task, count + 1))
                print(f"[FixMemory] Strengthened: {pattern} → {action} (task: {task})")
                return

        self.knowledge[pattern].append((action, task, 1))
        print(f"[FixMemory] Learned: {pattern} → {action} (task: {task})")

    def record_success(self, pattern: str, task: str = ""):
        """Record that a certain error pattern was successfully resolved"""
        pattern = pattern.strip().lower()
        task = task.strip().lower()
        self.success_patterns.add(pattern)
        self.record(pattern, "success", task)

    def find_best_action(self, text: str, task: str = "") -> dict | None:
        """Find the best known fix for the current error text"""
        if not text:
            return None

        text = text.lower().strip()
        task = task.strip().lower()

        best = None
        best_conf = 0.0

        for pattern, entries in self.knowledge.items():
            # Check if pattern matches the current error
            if pattern in text or any(word in text for word in pattern.split()):
                for action, entry_task, count in entries:
                    # Higher confidence if task matches or it's a success pattern
                    conf = 0.5
                    if entry_task and entry_task in task:
                        conf += 0.4
                    if action == "success" or pattern in self.success_patterns:
                        conf += 0.3
                    if count > 1:
                        conf += 0.2 * (count - 1)  # more occurrences = higher confidence

                    if conf > best_conf:
                        best_conf = conf
                        best = {
                            "action": action,
                            "confidence": round(conf, 2),
                            "pattern": pattern
                        }

        if best:
            print(f"[FixMemory] 🧠 Best match: '{best['pattern']}' → {best['action']} (conf: {best['confidence']})")
            return best

        return None

    def clear(self):
        """Reset memory (useful for testing)"""
        self.knowledge.clear()
        self.success_patterns.clear()
        print("[FixMemory] Memory cleared")