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