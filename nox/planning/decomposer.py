from nox.contracts.task import Task
from .task_graph import TaskGraph


class TaskDecomposer:

    def decompose(self, prompt: str):

        prompt = prompt.lower()

        graph = TaskGraph()

        if "app" in prompt:

            design = Task("design", "planner", "design application structure")
            code = Task("code", "coder", prompt)
            test = Task("test", "tester", "test generated code")
            review = Task("review", "reviewer", "review code quality")
            fix = Task("fix", "fixer", "fix detected issues")
            assemble = Task("assemble", "assembler", "assemble final project")

            code.add_dependency(design)
            test.add_dependency(code)
            review.add_dependency(test)
            fix.add_dependency(review)
            assemble.add_dependency(fix)

            for t in [design, code, test, review, fix, assemble]:
                graph.add(t)

        else:

            task = Task("general", "chat", prompt)
            graph.add(task)

        return graph