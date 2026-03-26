from .lily_brain import Lily


class LilyAgent:
    def __init__(self, runtime=None, llm=None):
        self.runtime = runtime
        self.brain = Lily(llm=llm)

        self.brain = Lily(user_name="NOX")

    async def run(self, task):

        return await self.brain.run(task)

        print(f"[LILY AGENT] Received: {prompt}")

        try:
            result = self.brain.step(prompt)

            # 🔁 If Lily returns dict (new god brain)
            if isinstance(result, dict):

                # Delegation
                if result.get("action") == "delegate":
                    return result

                # Direct response
                return {
                    "message": result.get("message", str(result)),
                    "results": result
                }

            # Fallback (string response)
            return {
                "message": str(result),
                "results": {}
            }

        except Exception as e:
            print(f"[LILY ERROR] {e}")
            return {
                "message": f"Lily crashed: {e}",
                "error": True
            }