class Memory:
    def __init__(self):
        self.store = {}

    def save(self, key, value):
        self.store[key] = value

    def load(self, key):
        return self.store.get(key)