import os
from pathlib import Path

print("Bootstrapping Forge V7...\n")

folders = [
    "forge",
    "forge/core",
    "forge/workers",
    "forge/arena",
    "forge/workspace",
]

files = {

"forge/__main__.py": """
import asyncio
from forge.arena.arena import main

if __name__ == "__main__":
    asyncio.run(main())
""",

"forge/arena/__main__.py": """
import asyncio
from .arena import main

if __name__ == "__main__":
    asyncio.run(main())
""",

"forge/core/workspace.py": """
from pathlib import Path

class Workspace:

    def __init__(self, root="forge/workspace"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def create_project(self, name="project"):
        project_path = self.root / name
        project_path.mkdir(parents=True, exist_ok=True)

        (project_path / "tests").mkdir(exist_ok=True)

        return project_path

    def write_file(self, project, file_path, content):

        full = project / file_path
        full.parent.mkdir(parents=True, exist_ok=True)

        with open(full, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"[Workspace] wrote {file_path}")
""",

"forge/workers/assembler.py": """
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
            "def test_main():\\n    assert True"
        )

        print("\\n===== FINAL PROJECT =====")
        print(project)
"""
}

# create folders
for folder in folders:
    Path(folder).mkdir(parents=True, exist_ok=True)

# create files
for file, content in files.items():

    path = Path(file)

    if not path.exists():

        with open(path, "w", encoding="utf-8") as f:
            f.write(content.strip())

        print("created:", file)

    else:
        print("exists :", file)

print("\nForge V7 bootstrap complete")
print("\nRun Forge with:")
print("python -m forge")