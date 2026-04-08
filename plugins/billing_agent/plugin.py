import sqlite3
from typing import Dict, Optional
import time

DEV_USERS = ["nox", "admin", "cosmic ethic"]  # Add your username here if needed

class BillingError(Exception):
    pass

class InsufficientCredits(BillingError):
    pass


class Billing:
    def __init__(self, db_path: str = "billing.db"):
        self.db_path = db_path

        self.costs = {
            "agent:lily": 2,
            "agent:web_agent": 5,
            "agent:coder": 50,
            "agent:researcher": 20,
            "agent:app_builder": 100,
            "system:build": 200,
        }

        self._init_db()

    # =========================================================
    # DB INIT + MIGRATION
    # =========================================================
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()

            c.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    credits INTEGER DEFAULT 0,
                    reserved INTEGER DEFAULT 0,
                    plan TEXT DEFAULT 'free',
                    is_admin INTEGER DEFAULT 0,
                    created_at REAL
                )
            """)

            # Safe migrations
            try:
                c.execute("ALTER TABLE users ADD COLUMN reserved INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass

            try:
                c.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass

            c.execute("""
                CREATE TABLE IF NOT EXISTS usage_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    action TEXT,
                    cost INTEGER,
                    timestamp REAL
                )
            """)

            conn.commit()

    # =========================================================
    # INTERNAL HELPERS
    # =========================================================
    def _is_dev(self, user_id: str) -> bool:
        return user_id in DEV_USERS

    def _get_or_create_user(self, c, user_id: str):
        if self._is_dev(user_id):
            return (999999, 0, "god_mode", 1)  # credits, reserved, plan, is_admin

        c.execute(
            "SELECT credits, reserved, plan, is_admin FROM users WHERE user_id=?",
            (user_id,)
        )
        row = c.fetchone()

        if row:
            return row

        # New normal user starts with 0 credits
        now = time.time()
        c.execute("""
            INSERT INTO users (user_id, credits, reserved, plan, is_admin, created_at)
            VALUES (?, 0, 0, 'free', 0, ?)
        """, (user_id, now))

        return (0, 0, "free", 0)

    # =========================================================
    # RESERVE / CAPTURE / RELEASE - DEV Optimized
    # =========================================================
    def reserve(self, user_id: str, amount: int) -> Dict:
        if self._is_dev(user_id):
            return {"status": "reserved", "admin": True, "dev_mode": True}

        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")

            credits, reserved, plan, is_admin = self._get_or_create_user(c, user_id)

            available = credits - reserved
            if available < amount:
                conn.rollback()
                return {"status": "blocked", "available": available}

            new_reserved = reserved + amount
            c.execute("UPDATE users SET reserved=? WHERE user_id=?", (new_reserved, user_id))
            conn.commit()

            return {"status": "reserved", "amount": amount, "reserved": new_reserved}

    def capture(self, user_id: str, amount: int) -> Dict:
        if self._is_dev(user_id):
            return {"status": "captured", "admin": True, "dev_mode": True}

        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")

            credits, reserved, plan, is_admin = self._get_or_create_user(c, user_id)

            new_reserved = max(0, reserved - amount)
            new_credits = credits - amount

            c.execute("UPDATE users SET credits=?, reserved=? WHERE user_id=?",
                      (new_credits, new_reserved, user_id))

            c.execute("INSERT INTO usage_logs (user_id, action, cost, timestamp) VALUES (?, ?, ?, ?)",
                      (user_id, "system:build", amount, time.time()))

            conn.commit()

            return {"status": "captured", "remaining": new_credits}

    def release(self, user_id: str, amount: int) -> Dict:
        if self._is_dev(user_id):
            return {"status": "released", "admin": True, "dev_mode": True}

        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")

            credits, reserved, plan, is_admin = self._get_or_create_user(c, user_id)
            new_reserved = max(0, reserved - amount)

            c.execute("UPDATE users SET reserved=? WHERE user_id=?", (new_reserved, user_id))
            conn.commit()

            return {"status": "released"}

    # =========================================================
    # GET BALANCE & ADD CREDITS
    # =========================================================
    def get_balance(self, user_id: str) -> Dict:
        if self._is_dev(user_id):
            return {
                "credits": 999999,
                "reserved": 0,
                "available": 999999,
                "plan": "god_mode",
                "is_admin": True
            }

        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""
                SELECT credits, reserved, plan, is_admin 
                FROM users WHERE user_id=?
            """, (user_id,))
            row = c.fetchone()

            if not row:
                return {
                    "credits": 0,
                    "reserved": 0,
                    "available": 0,
                    "plan": "free",
                    "is_admin": False
                }

            credits, reserved, plan, is_admin = row
            return {
                "credits": credits,
                "reserved": reserved,
                "available": credits - reserved,
                "plan": plan,
                "is_admin": bool(is_admin)
            }

    def add_credits(self, user_id: str, amount: int) -> Dict:
        if self._is_dev(user_id):
            return {"status": "added", "credits": 999999, "note": "dev_user_unlimited"}

        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")

            credits, reserved, plan, is_admin = self._get_or_create_user(c, user_id)
            new_credits = credits + amount

            c.execute("UPDATE users SET credits=? WHERE user_id=?", (new_credits, user_id))
            conn.commit()

        return {"status": "added", "credits": new_credits}


def register(runtime):
    billing = Billing()
    runtime.register_agent("billing_agent", billing)
    print("[PLUGIN] Billing agent registered")