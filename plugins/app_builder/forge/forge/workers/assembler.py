from forge.core.workspace import Workspace

class Assembler:

    def __init__(self, bus):
        self.bus = bus
        self.workspace = Workspace()

        bus.subscribe("REVIEW_APPROVED", self.handle)

    async def handle(self, message):

        print("[Assembler] received REVIEW_APPROVED")

        project = self.workspace.create_project()

        self.workspace.write_file(
            project,
            "main.py",
            "print('Hello from Forge project')"
        )

        self.workspace.write_file(
            project,
            "tests/test_main.py",
            "def test_main():\n    assert True"
        )

        print("\n===== FINAL PROJECT =====")
        print(project)