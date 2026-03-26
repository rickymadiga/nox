from nox.core.tools import ToolManager


class Registry:

    def __init__(self):

        self._agents = {}

        # Inject tool manager
        self.tools = ToolManager(self)

    # -------------------------

    def register(self, name, agent):

        self._agents[name] = agent

    # -------------------------

    def get(self, name):

        return self._agents.get(name)

    # -------------------------

    def list_agents(self):

        return list(self._agents.keys())