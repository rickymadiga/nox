import asyncio
import traceback


class AsyncRuntimeLoop:

    def __init__(self, engine):
        self.engine = engine
        self.running = True

    async def handle_user_input(self):

        while self.running:
            try:
                user_input = await asyncio.to_thread(
                    input,
                    "\nNOX (async) > "
                )

                if user_input.lower() in ["exit", "quit", "stop"]:
                    self.running = False
                    break

                await self.engine.handle_user_request_async(user_input)

            except Exception:
                print(traceback.format_exc())

    async def start(self):

        print("🌌 NOX ASYNC RUNTIME STARTED")

        await asyncio.sleep(1)