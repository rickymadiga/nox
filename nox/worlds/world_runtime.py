import asyncio
import traceback


class WorldRuntime:

    def __init__(self, engine, world_manager):

        self.engine = engine
        self.world_manager = world_manager
        self.running = True

    async def run_world(self, world):

        while self.running:

            try:
                await asyncio.sleep(0.1)

                # Future: world simulation ticks go here
                world.log_event("world_tick")

            except Exception:
                print(traceback.format_exc())

    async def start(self):

        print("🌍 Distributed NOX Worlds Starting")

        tasks = []

        for world in self.world_manager.worlds.values():

            tasks.append(
                asyncio.create_task(self.run_world(world))
            )

        await asyncio.gather(*tasks)