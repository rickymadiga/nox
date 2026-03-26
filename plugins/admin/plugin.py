# plugins/admin_agent/plugin.py

import sqlite3
import time
from typing import Dict, List


class AdminAgent:
    def __init__(self, db_path="billing.db"):
        self.db_path = db_path
        self._init_db()

    # =========================================================
    # DATABASE HELPER
    # =========================================================
    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Ensure all required tables exist"""
        with self._connect() as conn:
            c = conn.cursor()

            # Users table (already exists from billing, but ensure columns)
            c.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    credits INTEGER DEFAULT 20,
                    plan TEXT DEFAULT 'free',
                    stripe_customer_id TEXT,
                    auto_recharge INTEGER DEFAULT 0,
                    created_at REAL
                )
            """)

            # Usage logs (from billing)
            c.execute("""
                CREATE TABLE IF NOT EXISTS usage_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    action TEXT,
                    cost INTEGER,
                    timestamp REAL
                )
            """)

            # Transactions table (for admin view)
            c.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    amount REAL,
                    credits INTEGER,
                    status TEXT,
                    created_at REAL
                )
            """)

            # Tickets table
            c.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    message TEXT,
                    status TEXT DEFAULT 'open',
                    created_at REAL
                )
            """)

            conn.commit()

    # =========================================================
    # USERS
    # =========================================================
    def get_all_users(self) -> List[Dict]:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT user_id, credits, plan, created_at
                FROM users
                ORDER BY created_at DESC
            """)
            rows = c.fetchall()

            return [
                {
                    "user_id": r[0],
                    "credits": r[1],
                    "plan": r[2],
                    "created_at": r[3]
                }
                for r in rows
            ]

    def get_user(self, user_id: str) -> Dict:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT user_id, credits, plan, created_at
                FROM users
                WHERE user_id=?
            """, (user_id,))
            row = c.fetchone()

            if not row:
                return {"error": "User not found"}

            return {
                "user_id": row[0],
                "credits": row[1],
                "plan": row[2],
                "created_at": row[3]
            }

    def add_credits(self, billing, user_id: str, amount: int):
        """Add credits to a user (used by admin)"""
        billing.add_credits(user_id, amount)
        return {"status": "ok", "message": f"Added {amount} credits to {user_id}"}

    def set_plan(self, user_id: str, plan: str):
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("""
                UPDATE users SET plan=? WHERE user_id=?
            """, (plan, user_id))
            conn.commit()
        return {"status": "ok"}

    # =========================================================
    # REVENUE & ANALYTICS
    # =========================================================
    def total_users(self) -> int:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM users")
            return c.fetchone()[0]

    def total_credits(self) -> int:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("SELECT SUM(credits) FROM users")
            result = c.fetchone()[0]
            return result if result else 0

    def total_revenue(self) -> float:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("SELECT SUM(cost) FROM usage_logs")
            result = c.fetchone()[0]
            return float(result or 0)

    def revenue_last_24h(self):
        now = time.time()
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT SUM(cost) FROM usage_logs WHERE timestamp > ?
            """, (now - 86400,))
            return c.fetchone()[0] or 0

    def top_users(self, limit=5):
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT user_id, SUM(cost) as total
                FROM usage_logs
                GROUP BY user_id
                ORDER BY total DESC
                LIMIT ?
            """, (limit,))
            return [
                {"user_id": r[0], "spent": r[1]}
                for r in c.fetchall()
            ]

    # =========================================================
    # ADVANCED ANALYTICS
    # =========================================================
    def revenue_timeseries(self, hours=24):
        now = time.time()
        since = now - (hours * 3600)

        with self._connect() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT timestamp, cost
                FROM usage_logs
                WHERE timestamp > ?
                ORDER BY timestamp ASC
            """, (since,))

            rows = c.fetchall()

        # Bucket by hour
        buckets = {}
        for ts, cost in rows:
            hour = int(ts // 3600) * 3600
            buckets[hour] = buckets.get(hour, 0) + cost

        return [
            {"time": k, "revenue": v}
            for k, v in sorted(buckets.items())
        ]

    def mrr_estimate(self):
        """Simple MRR estimation from plans"""
        plan_prices = {
            "free": 0,
            "starter": 5,
            "pro": 20,
            "mega": 50
        }

        with self._connect() as conn:
            c = conn.cursor()
            c.execute("SELECT plan, COUNT(*) FROM users GROUP BY plan")
            rows = c.fetchall()

        total = 0
        breakdown = {}

        for plan, count in rows:
            price = plan_prices.get(plan, 0)
            total += price * count
            breakdown[plan] = count

        return {
            "mrr": total,
            "breakdown": breakdown
        }

    # =========================================================
    # TRANSACTIONS
    # =========================================================
    def get_transactions(self, limit=50):
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT user_id, action, cost, timestamp
                FROM usage_logs
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            return [
                {
                    "user_id": r[0],
                    "action": r[1],
                    "cost": r[2],
                    "timestamp": r[3]
                }
                for r in c.fetchall()
            ]

    # =========================================================
    # SUPPORT TICKETS
    # =========================================================
    def create_ticket(self, user_id: str, message: str):
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO tickets (user_id, message, status, created_at)
                VALUES (?, ?, 'open', ?)
            """, (user_id, message, time.time()))
            conn.commit()
        return {"status": "created"}

    def get_tickets(self):
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT id, user_id, message, status, created_at
                FROM tickets
                ORDER BY created_at DESC
            """)
            return [
                {
                    "id": r[0],
                    "user_id": r[1],
                    "message": r[2],
                    "status": r[3],
                    "created_at": r[4]
                }
                for r in c.fetchall()
            ]

    def resolve_ticket(self, ticket_id: int):
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("""
                UPDATE tickets SET status='resolved' WHERE id=?
            """, (ticket_id,))
            conn.commit()
        return {"status": "resolved"}

    # =========================================================
    # FRAUD / ABUSE DETECTION
    # =========================================================
    def detect_abuse(self):
        with self._connect() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT user_id, COUNT(*) as calls
                FROM usage_logs
                WHERE timestamp > ?
                GROUP BY user_id
                HAVING calls > 100
            """, (time.time() - 3600,))
            return [
                {"user_id": r[0], "calls_last_hour": r[1]}
                for r in c.fetchall()
            ]

    # =========================================================
    # SYSTEM HEALTH
    # =========================================================
    def health(self):
        return {
            "status": "ok",
            "time": time.time()
        }

    # =========================================================
    # MASTER DASHBOARD STATS
    # =========================================================
    def get_dashboard(self):
        return {
            "users": self.total_users(),
            "credits": self.total_credits(),
            "revenue_total": self.total_revenue(),
            "revenue_24h": self.revenue_last_24h(),
            "top_users": self.top_users(),
            "abuse": self.detect_abuse()
        }


# =========================================================
# REGISTER
# =========================================================
def register(runtime):
    agent = AdminAgent()
    runtime.register_agent("admin_agent", agent)
    print("[PLUGIN] Admin Agent (Enterprise Dashboard) loaded 🧠💼")