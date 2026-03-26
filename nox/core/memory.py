class AgentMemory:
    """
    Shared memory for agents.
    Agents can store and retrieve information during tasks.
    """

    def __init__(self):
        self.storage = {}

    def write(self, key, value):
        self.storage[key] = value

    def read(self, key):
        return self.storage.get(key)

    def append(self, key, value):

        if key not in self.storage:
            self.storage[key] = []

        if not isinstance(self.storage[key], list):
            self.storage[key] = [self.storage[key]]

        self.storage[key].append(value)

    def all(self):
        return self.storage