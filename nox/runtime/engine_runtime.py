async def handle_prompt(self, prompt: str, user_id: str) -> Dict[str, Any]:
    if not prompt.strip():
        return {"status": "error", "response": "Empty prompt"}

    task = {
        "prompt": prompt,
        "intent": "user_prompt",
        "user_id": user_id   # ✅ REAL USER
    }

    lily = self.runtime.get_agent("lily")
    billing = self.runtime.get_agent("billing_agent")
    monetizer = self.runtime.get_agent("monetization_agent")

    if not lily:
        return {"status": "error", "response": "Lily not available"}

    try:
        # =========================
        # 1. LILY DECIDES
        # =========================
        lily_res = lily.run(task)
        if asyncio.iscoroutine(lily_res):
            lily_res = await lily_res

        if not isinstance(lily_res, dict):
            return {
                "status": "success",
                "response": str(lily_res)
            }

        action = lily_res.get("action", "respond")

        # =========================
        # 2. BILLING CHECK (WITH ADMIN BYPASS 🔥)
        # =========================
        cost = 0
        is_admin = False

        if billing:
            user_data = billing._get_user(user_id)
            is_admin = user_data.get("is_admin", False)

            if not is_admin:
                bill_res = billing.run({
                    "user_id": user_id,
                    "action": action
                })

                if isinstance(bill_res, dict) and bill_res.get("status") == "blocked":
                    upsell_msg = None
                    trigger = None

                    if monetizer:
                        upsell = monetizer.run({
                            "user_id": user_id,
                            "action": action,
                            "success": False
                        })

                        if isinstance(upsell, dict) and upsell.get("upsell"):
                            upsell_msg = upsell.get("message")
                            trigger = upsell.get("trigger")

                    return {
                        "status": "error",
                        "response": bill_res.get("message", "Not enough credits"),
                        "upsell": upsell_msg,
                        "trigger": trigger
                    }

                cost = bill_res.get("cost", 0) if isinstance(bill_res, dict) else 0
            else:
                print(f"[ADMIN BYPASS] {user_id} skipping billing")

        # =========================
        # 3. EXECUTE ACTION
        # =========================
        results = None

        if action == "respond":
            final_response = lily_res.get("message") or "Done."

        elif action == "delegate":
            target = lily_res.get("target")
            if not target:
                return {"status": "error", "response": "No target specified"}

            results = await self.runtime.execute_agents([target], task)
            final_response = self._synthesize(results)

        elif action == "delegate_multi":
            targets = lily_res.get("targets", [])
            if not targets:
                return {"status": "error", "response": "No targets provided"}

            results = await self.runtime.execute_agents(targets, task)
            final_response = self._synthesize(results)

        elif action == "orchestrate":
            agents = self.runtime.capabilities.match(prompt)
            if not agents:
                return {
                    "status": "success",
                    "response": "No suitable agent found."
                }

            results = await self.runtime.execute_agents(agents, task)
            final_response = self._synthesize(results)

        else:
            final_response = lily_res.get("message", "Done.")

        # =========================
        # 4. AUTO RECHARGE (SKIP FOR ADMIN 🔥)
        # =========================
        if billing and not is_admin:
            user_data = billing._get_user(user_id)

            if user_data.get("credits", 0) < 5 and user_data.get("auto_recharge"):
                stripe_agent = self.runtime.get_agent("stripe_agent")

                if stripe_agent:
                    try:
                        stripe_agent.auto_charge(user_id=user_id, amount=500)
                        billing.add_credits(user_id, 100)
                        print(f"[AUTO-RECHARGE] Triggered for {user_id}")
                    except Exception as e:
                        print(f"[AUTO-RECHARGE FAILED] {e}")

        # =========================
        # 5. MONETIZATION
        # =========================
        upsell_msg = None
        trigger = None

        if monetizer and not is_admin:
            upsell = monetizer.run({
                "user_id": user_id,
                "action": action,
                "success": True
            })

            if isinstance(upsell, dict) and upsell.get("upsell"):
                upsell_msg = upsell.get("message")
                trigger = upsell.get("trigger")

        # =========================
        # FINAL RESPONSE
        # =========================
        return {
            "status": "success",
            "response": final_response,
            "upsell": upsell_msg,
            "trigger": trigger,
            "results": results
        }

    except Exception as e:
        logger.error(f"[ENGINE ERROR] {e}", exc_info=True)
        return {
            "status": "error",
            "response": f"Internal error: {str(e)}"
        }