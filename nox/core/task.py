class Task:

    def __init__(self, prompt):

        self.prompt = prompt
        self.context = {}


    def clone(self, new_prompt):

        t = Task(new_prompt)

        t.context = self.context.copy()

        return t