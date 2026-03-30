import os
import datetime
import shutil
from typing import Any, Dict

from ..core.agent import Agent
from ..core.message import Message


class Assembler(Agent):
    """
    Final pipeline stage: Assembles approved code into a proper project folder.
    Then zips it and provides a download link.
    """

    OUTPUT_BASE_DIR = "generated_apps"
    TEMPLATE_DIR_BASE = "forge/templates"

    def __init__(self, runtime):
        # Updated constructor to match new Arena style
        self.runtime = runtime
        self.bus = runtime.bus
        self.name = "assembler"
        self.template_type = "default"   # Make this dynamic later if needed

        # Subscribe to CODE_APPROVED
        self.bus.subscribe("CODE_APPROVED", self.on_code_approved)

    def register(self) -> None:
        print("[Assembler] Subscribed to CODE_APPROVED")

    async def on_code_approved(self, message: Message) -> None:
        if message.message_type != "CODE_APPROVED":
            return

        print("[Assembler] Received CODE_APPROVED → Starting final assembly")

        payload = message.payload or {}

        files: Dict[str, str] = payload.get("files", {})
        task: str = payload.get("task", "generated_app").strip()
        user_id: str = payload.get("user_id", "unknown")

        if not files:
            print("[Assembler] No files received → build skipped")
            return

        # Create unique project directory
        safe_task = (
            task.lower()
            .replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
            .strip("_")[:50]
        )
        if not safe_task:
            safe_task = "app"

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        project_name = f"{safe_task}_{timestamp}"
        project_dir = os.path.join(self.OUTPUT_BASE_DIR, project_name)

        os.makedirs(project_dir, exist_ok=True)
        print(f"[Assembler] Creating project: {project_dir}")

        # 1. Write all generated files (with subdirectory support)
        self._write_files(project_dir, files)

        # 2. Copy template files (gitignore, requirements.txt, etc.)
        self._copy_template_files(project_dir)

        # 3. Generate helpful README
        self._generate_readme(project_dir, task)

        print("\n" + "=" * 50)
        print(" BUILD COMPLETE ".center(50))
        print(f" Project     : {project_name}")
        print(f" Location    : {project_dir}")
        print("=" * 50 + "\n")

        # 🔥 ZIP THE PROJECT
        try:
            zip_base = os.path.join(self.OUTPUT_BASE_DIR, project_name)
            zip_path = shutil.make_archive(zip_base, 'zip', project_dir)

            download_url = f"/download/{project_name}"

            print(f"[Assembler] Project zipped successfully → {zip_path}")
            print(f"[Assembler] Download URL: {download_url}")

            # 🔥 PUBLISH FINAL EVENT SO FRONTEND CAN SHOW DOWNLOAD LINK
            await self.bus.publish(
                Message(
                    sender=self.name,
                    recipient="arena",           # or directly to frontend via event
                    message_type="forge_complete",
                    payload={
                        "status": "success",
                        "message": f"✅ Project '{project_name}' is ready!",
                        "project_name": project_name,
                        "download_url": download_url,
                        "project_path": project_dir,
                        "user_id": user_id,
                    }
                )
            )

        except Exception as e:
            print(f"[Assembler] Failed to create zip: {e}")
            await self.bus.publish(
                Message(
                    sender=self.name,
                    recipient="arena",
                    message_type="forge_complete",
                    payload={
                        "status": "error",
                        "message": "Failed to package project",
                        "user_id": user_id,
                    }
                )
            )

    def _write_files(self, project_dir: str, files: Dict[str, str]) -> None:
        """Write all files from the payload, creating subdirectories as needed."""
        for rel_path, content in files.items():
            if not rel_path or not isinstance(content, str):
                continue

            full_path = os.path.join(project_dir, rel_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            try:
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content.rstrip() + "\n")
                print(f"[Assembler] Wrote: {rel_path}")
            except Exception as e:
                print(f"[Assembler] Failed to write {rel_path}: {e}")

    def _copy_template_files(self, project_dir: str) -> None:
        """Copy files from the selected template directory."""
        template_dir = os.path.join(self.TEMPLATE_DIR_BASE, self.template_type)

        if not os.path.isdir(template_dir):
            print(f"[Assembler] Template not found: {template_dir} (skipping)")
            return

        print(f"[Assembler] Copying template files from: {template_dir}")

        for item in os.listdir(template_dir):
            src = os.path.join(template_dir, item)
            dst = os.path.join(project_dir, item)

            try:
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                    print(f"[Assembler] Copied: {item}")
                elif os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                    print(f"[Assembler] Copied directory: {item}/")
            except Exception as e:
                print(f"[Assembler] Failed to copy {item}: {e}")

    def _generate_readme(self, project_dir: str, task: str) -> None:
        """Generate a helpful README.md"""
        readme_path = os.path.join(project_dir, "README.md")

        content = f"""# {task.title()}

Generated by **NOX Forge** on {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Overview
This project was automatically generated from the task:

**{task}**

## How to Run

```bash
# 1. Navigate to the project directory
cd {os.path.basename(project_dir)}

# 2. Create and activate virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate          # Linux / macOS
# .venv\\Scripts\\activate        # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
python main.py
"""