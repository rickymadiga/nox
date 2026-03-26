import re

class CalculatorTool:

    name = "calculator"

    def can_handle(self, prompt: str) -> bool:
        return bool(re.search(r"[0-9\+\-\*/\(\)]", prompt))

    def run(self, prompt: str):

        try:
            expression = re.findall(r"[0-9\+\-\*/\(\)\.]+", prompt)
            expression = "".join(expression)

            result = eval(expression)

            return str(result)

        except Exception:
            return "Invalid math expression"