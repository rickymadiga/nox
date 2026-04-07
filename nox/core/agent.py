class Agent:
    def __init__(self, runtime):
        self.runtime = runtime
        self.bus = runtime.bus
        self.name = self.__class__.__name__.lower()

    async def run(self, *args, **kwargs):
        raise NotImplementedError("Agent must implement run()")