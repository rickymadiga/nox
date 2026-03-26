class Task:

    def __init__(self, name, agent, prompt):
        self.name = name
        self.agent = agent
        self.prompt = prompt
        self.dependencies = []
        self.completed = False

    def add_dependency(self, task):
        self.dependencies.append(task)

    def ready(self):
        return all(dep.completed for dep in self.dependencies)