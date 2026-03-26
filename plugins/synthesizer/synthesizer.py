class SynthesizerAgent:

    def __init__(self, runtime):
        self.runtime = runtime

    async def run(self, task):

        results = task.get("results", {})

        messages = []

        for agent, output in results.items():

            if agent == "weather":

                time = output.get("current_time", "")
                temp = output.get("temperature", "")

                if time:
                    messages.append(f"The current time is {time}.")

                if temp:
                    messages.append(f"The temperature is {temp}°C.")

            elif agent == "app_builder":

                app_type = output.get("app_type", "application")

                messages.append(
                    f"I created a {app_type} for you. The generated code is ready."
                )

            elif agent == "humor":

                joke = output.get("joke", "")

                if joke:
                    messages.append(joke)

            elif agent == "notification":

                message = output.get("message", "")

                if message:
                    messages.append(message)

            else:

                messages.append(str(output))

        final_response = " ".join(messages)

        return {
            "type": "synthesized_response",
            "message": final_response,
            "sources": list(results.keys())
        }