# plugins/billing_agent/plugin.py

import sqlite3
import threading
import time


class BillingAgent:
    def __init__(self, db_path="billing.db"):
        self.db_path = db_path
        self.lock = threading.Lock()

        # 🔥 Cost per action (tune anytime)
        self.costs = {
            "delegate": 5,
            "delegate_multi": 7,
            "orchestrate": 10,
            "respond": 0
        }

        self._init_db()

    
    # =========================================================
    # DATABASE INIT - Robust schema migration
    # =========================================================
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()

            # Users table (with admin flag)
            c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                credits INTEGER DEFAULT 20,
                plan TEXT DEFAULT 'free',
                stripe_customer_id TEXT,
                auto_recharge INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                created_at REAL
            )
            """)

            # Usage logs
            c.execute("""
            CREATE TABLE IF NOT EXISTS usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                action TEXT,
                cost INTEGER,
                timestamp REAL
            )
            """)

            # Transactions table
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

            # ────── Safe schema migration for is_admin ──────
            # Check if is_admin column exists
            c.execute("PRAGMA table_info(users)")
            columns = [info[1] for info in c.fetchall()]   # info[1] = column name

            if "is_admin" not in columns:
                print("[Billing] Adding missing 'is_admin' column...")
                c.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")

                # Make default_user an admin (one-time)
                c.execute("""
                    UPDATE users 
                    SET is_admin = 1 
                    WHERE user_id = 'default_user'
                """)
                print("[Billing] 'default_user' promoted to admin")

            # Also ensure existing users have is_admin = 0 if somehow NULL
            c.execute("UPDATE users SET is_admin = 0 WHERE is_admin IS NULL")

            conn.commit()

    # =========================================================
    # USER GET / CREATE (Updated to include is_admin)
    # =========================================================
    def _get_user(self, user_id):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()

            c.execute(
                "SELECT credits, plan, stripe_customer_id, auto_recharge, is_admin FROM users WHERE user_id=?",
                (user_id,)
            )
            row = c.fetchone()

            if row:
                return {
                    "credits": row[0],
                    "plan": row[1],
                    "stripe_customer_id": row[2],
                    "auto_recharge": bool(row[3]),
                    "is_admin": bool(row[4])
                }

            # 🔥 Auto-create user (default non-admin)
            now = time.time()
            c.execute(
                "INSERT INTO users (user_id, credits, plan, stripe_customer_id, auto_recharge, is_admin, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, 20, "free", None, 0, 0, now)
            )
            conn.commit()

            return {
                "credits": 20,
                "plan": "free",
                "stripe_customer_id": None,
                "auto_recharge": False,
                "is_admin": False
            }

    # =========================================================
    # UPDATE CREDITS
    # =========================================================
    def _update_credits(self, user_id, new_credits):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                "UPDATE users SET credits=? WHERE user_id=?",
                (new_credits, user_id)
            )
            conn.commit()

    # =========================================================
    # LOG USAGE
    # =========================================================
    def _log_usage(self, user_id, action, cost):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO usage_logs (user_id, action, cost, timestamp) VALUES (?, ?, ?, ?)",
                (user_id, action, cost, time.time())
            )
            conn.commit()

    # =========================================================
    # SET AUTO RECHARGE
    # =========================================================
    def set_auto_recharge(self, user_id, enabled: bool):
        """Enable or disable auto-recharge for a user"""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                "UPDATE users SET auto_recharge=? WHERE user_id=?",
                (1 if enabled else 0, user_id)
            )
            conn.commit()
        print(f"[Billing] Auto-recharge for user {user_id} set to: {enabled}")

    # =========================================================
    # AUTO RECHARGE LOGIC
    # =========================================================
    def auto_recharge_if_needed(self, user_id):
        """Automatically recharge user if credits are low"""
        user = self._get_user(user_id)

        if user["credits"] > 5:
            return

        if not user.get("stripe_customer_id"):
            print(f"[AUTO-RECHARGE] User {user_id} has no payment method")
            return

        if not user.get("auto_recharge"):
            print(f"[AUTO-RECHARGE] Auto-recharge is disabled for user {user_id}")
            return

        stripe_agent = self.runtime.get_agent("stripe_agent")

        try:
            stripe_agent.auto_charge(user["stripe_customer_id"], 1000)  # $10.00

            # Add credits after successful charge
            self.add_credits(user_id, 100)

            print(f"[AUTO-RECHARGE] User {user_id} charged +100 credits")

        except Exception as e:
            print(f"[AUTO-RECHARGE FAILED] {user_id}: {e}")

    # =========================================================
    # ADD CREDITS
    # =========================================================
    def add_credits(self, user_id, amount: int):
        """Add credits to user"""
        with self.lock:
            user = self._get_user(user_id)
            new_credits = user["credits"] + amount
            self._update_credits(user_id, new_credits)
            print(f"[CREDITS] Added {amount} credits to {user_id}. New balance: {new_credits}")

    # =========================================================
    # CHECK BEFORE EXECUTION (Updated with ADMIN BYPASS)
    # =========================================================
    def check(self, user_id, action):
        user = self._get_user(user_id)

        # 🚀 ADMIN BYPASS - Full access, no cost
        if user.get("is_admin"):
            return {
                "status": "allowed",
                "cost": 0,
                "remaining": 999999,
                "admin": True
            }

        base_cost = self.costs.get(action, 1)

        # Plan-based pricing
        if user["plan"] == "pro":
            cost = int(base_cost * 0.5)
        else:
            cost = base_cost

        if user["credits"] < cost:
            return {
                "status": "blocked",
                "message": f"Not enough credits 💳 (You have {user['credits']})"
            }

        return {
            "status": "allowed",
            "cost": cost,
            "remaining": user["credits"]
        }

    # =========================================================
    # CHARGE AFTER EXECUTION (Updated with ADMIN BYPASS)
    # =========================================================
    def charge(self, user_id, action, cost):
        user = self._get_user(user_id)

        # 🚀 ADMIN NEVER CHARGED
        if user.get("is_admin"):
            return {
                "status": "admin_free",
                "remaining": 999999
            }

        with self.lock:
            new_credits = user["credits"] - cost
            if new_credits < 0:
                new_credits = 0

            self._update_credits(user_id, new_credits)
            self._log_usage(user_id, action, cost)

            # Trigger auto-recharge if needed
            if new_credits <= 5:
                self.auto_recharge_if_needed(user_id)

            return {
                "status": "charged",
                "remaining": new_credits
            }

    # =========================================================
    # MAIN ENTRY (USED BY ENGINE)
    # =========================================================
    def run(self, task):
        user_id = task.get("user_id", "default_user")
        action = task.get("action", "respond")

        # Support for setting auto-recharge from frontend
        if action == "set_auto_recharge":
            enabled = task.get("enabled", False)
            self.set_auto_recharge(user_id, enabled)
            return {"status": "success", "message": f"Auto-recharge set to {enabled}"}

        return self.check(user_id, action)


# =========================================================
# REGISTER (PLUGIN LOADER ENTRY)
# =========================================================
def register(runtime):
    agent = BillingAgent()
    # Make runtime available for auto_recharge and stripe calls
    agent.runtime = runtime
    runtime.register_agent("billing_agent", agent)

    print("[PLUGIN] Billing Agent (SQLite + Auto-Recharge + Admin Bypass) loaded 💳")