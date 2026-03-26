# plugins/stripe_agent/plugin.py

import stripe
import os
import time
import sqlite3
from dotenv import load_dotenv

load_dotenv()


class StripeAgent:
    def __init__(self):
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        self.endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

        # 💰 Plan → credits mapping
        self.plans = {
            "starter": {"amount": 500, "credits": 50},   # $5
            "pro": {"amount": 2000, "credits": 250},     # $20
            "mega": {"amount": 5000, "credits": 800}     # $50
        }

        self.db_path = "billing.db"  # shared with billing agent

    # =========================================================
    # CREATE CHECKOUT SESSION (BUY CREDITS)
    # =========================================================
    def create_checkout_session(self, user_id, plan):
        if plan not in self.plans:
            return {"error": "Invalid plan"}

        plan_data = self.plans[plan]

        try:
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                mode="payment",
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"{plan.capitalize()} Credits"
                        },
                        "unit_amount": plan_data["amount"],
                    },
                    "quantity": 1,
                }],
                metadata={
                    "user_id": user_id,
                    "plan": plan,
                    "credits": plan_data["credits"]
                },
                success_url="http://localhost:8501?success=true",
                cancel_url="http://localhost:8501?canceled=true"
            )

            return {"url": session.url}

        except Exception as e:
            return {"error": str(e)}

    # =========================================================
    # CREATE CUSTOMER (FOR AUTO BILLING)
    # =========================================================
    def create_customer(self, user_id, email="user@nox.ai"):
        try:
            customer = stripe.Customer.create(
                email=email,
                metadata={"user_id": user_id}
            )
            return customer.id
        except Exception as e:
            return {"error": str(e)}

    # =========================================================
    # SETUP PAYMENT METHOD (SAVE CARD)
    # =========================================================
    def create_setup_session(self, customer_id):
        try:
            session = stripe.checkout.Session.create(
                mode="setup",
                customer=customer_id,
                payment_method_types=["card"],
                success_url="http://localhost:8501?setup=success",
                cancel_url="http://localhost:8501?setup=cancel"
            )
            return {"url": session.url}
        except Exception as e:
            return {"error": str(e)}

    # =========================================================
    # AUTO CHARGE (OFF-SESSION)
    # =========================================================
    def auto_charge(self, customer_id, amount=1000):
        """Charge customer off-session (for auto-recharge)"""
        try:
            intent = stripe.PaymentIntent.create(
                amount=amount,  # in cents
                currency="usd",
                customer=customer_id,
                off_session=True,
                confirm=True
            )
            return intent
        except Exception as e:
            print(f"[Stripe Auto Charge Failed] {e}")
            return {"error": str(e)}

    # =========================================================
    # HANDLE WEBHOOK
    # =========================================================
    def handle_webhook(self, payload, sig_header):
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.endpoint_secret
            )
        except Exception as e:
            print("[STRIPE WEBHOOK ERROR]", str(e))
            return {"status": "error"}

        # 💳 PAYMENT SUCCESS (CHECKOUT)
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]

            user_id = session["metadata"].get("user_id")
            credits = int(session["metadata"].get("credits", 0))

            return {
                "action": "add_credits",
                "user_id": user_id,
                "credits": credits
            }

        # ⚡ AUTO CHARGE SUCCESS
        if event["type"] == "payment_intent.succeeded":
            intent = event["data"]["object"]
            customer_id = intent.get("customer")

            return {
                "action": "auto_topup",
                "customer_id": customer_id,
                "credits": 100
            }

        return {"status": "ignored"}

    # =========================================================
    # LOG TRANSACTION (Your new block)
    # =========================================================
    def log_transaction(self, user_id, amount, credits, status="success"):
        """Log transaction to shared billing database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()

                c.execute("""
                    INSERT INTO transactions (user_id, amount, credits, status, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, amount, credits, status, time.time()))

                conn.commit()

            print(f"[Stripe] Transaction logged for {user_id}: +{credits} credits")
        except Exception as e:
            print(f"[Stripe Log Transaction Failed] {e}")

    # =========================================================
    # HELPER: MAP CUSTOMER → USER
    # =========================================================
    def get_user_from_customer(self, customer_id):
        try:
            customer = stripe.Customer.retrieve(customer_id)
            return customer["metadata"].get("user_id")
        except:
            return None

    # =========================================================
    # ENTRY POINT (OPTIONAL)
    # =========================================================
    def run(self, task):
        action = task.get("action")

        if action == "create_checkout":
            return self.create_checkout_session(
                task["user_id"],
                task["plan"]
            )

        if action == "setup_payment":
            return self.create_setup_session(
                task["customer_id"]
            )

        return {"status": "idle"}


# =========================================================
# REGISTER
# =========================================================
def register(runtime):
    agent = StripeAgent()
    runtime.register_agent("stripe_agent", agent)

    print("[PLUGIN] Stripe Agent loaded 💳")