from nox.contracts.task import Task


class TaskGraph:

    def __init__(self):
        self.tasks = []

    def add(self, task: Task):
        self.tasks.append(task)

    def get_ready_tasks(self):

        ready = []

        for task in self.tasks:

            if task.completed:
                continue

            if task.ready():
                ready.append(task)

        return ready

    def done(self):
        return all(task.completed for task in self.tasks)