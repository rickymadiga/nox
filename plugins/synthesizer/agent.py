class SynthesizerAgent:

    def __init__(self, runtime):
        self.runtime = runtime


    async def run(self, task):

        results = task.get("results", {})

        # ---- Analytics formatting ----
        if "analytics" in results and "error" not in results["analytics"]:

            data = results["analytics"]

            avg = data.get("average")
            count = data.get("count")
            total = data.get("sum")
            minimum = data.get("min")
            maximum = data.get("max")

            message = f"""
Average: {avg}

Dataset Summary
• Count: {count}
• Sum: {total}
• Min: {minimum}
• Max: {maximum}
""".strip()

            return message


        # ---- Calculator formatting ----
        if "calculator" in results and "error" not in results["calculator"]:

            calc = results["calculator"]

            expression = calc.get("expression")
            result = calc.get("result")

            return f"{expression} = {result}"


        # ---- Error fallback ----
        responses = []

        for agent, result in results.items():

            if isinstance(result, dict) and "error" in result:
                responses.append(f"{agent} error: {result['error']}")
            else:
                responses.append(str(result))

        return "\n".join(responses)