import os
import datetime
import shutil
from typing import Dict


class Assembler:
    """
    Final pipeline stage: Assembles approved code into a proper project folder,
    zips it, and emits a download link.
    """

    OUTPUT_BASE_DIR = "generated_apps"
    TEMPLATE_DIR_BASE = "forge/templates"

    def __init__(self, bus, context):
        self.bus = bus
        self.context = context
        self.name = "assembler"
        self.template_type = "default"

        # Subscribe to CODE_APPROVED event
        self.bus.subscribe("CODE_APPROVED", self.on_code_approved)

        print("[Assembler] Subscribed to CODE_APPROVED")

    def register(self) -> None:
        print("[Assembler] Registered")

    # ─────────────────────────────────────────────
    async def on_code_approved(self, message: dict) -> None:
        if message.get("type") != "CODE_APPROVED":
            return

        print("[Assembler] Received CODE_APPROVED → Starting final assembly")

        payload = message.get("payload", {})

        files: Dict[str, str] = payload.get("files", {})
        task: str = payload.get("task", "generated_app").strip()
        user_id: str = payload.get("user_id", "unknown")

        if not files:
            print("[Assembler] No files received → build skipped")
            return

        # ─────────────────────────────────────────
        # Create project directory
        safe_task = (
            task.lower()
            .replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
            .strip("_")[:50]
        ) or "app"

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        project_name = f"{safe_task}_{timestamp}"

        project_dir = os.path.join(self.OUTPUT_BASE_DIR, project_name)
        os.makedirs(project_dir, exist_ok=True)

        print(f"[Assembler] Creating project: {project_dir}")

        # ─────────────────────────────────────────
        # 1. Write generated files
        self._write_files(project_dir, files)

        # 2. Copy templates
        self._copy_template_files(project_dir)

        # 3. Generate README
        self._generate_readme(project_dir, task)

        print("\n" + "=" * 50)
        print(" BUILD COMPLETE ".center(50))
        print(f" Project     : {project_name}")
        print(f" Location    : {project_dir}")
        print("=" * 50 + "\n")

        # ─────────────────────────────────────────
        # ZIP PROJECT
        try:
            zip_base = os.path.join(self.OUTPUT_BASE_DIR, project_name)
            zip_path = shutil.make_archive(zip_base, 'zip', project_dir)

            download_url = f"/download/{project_name}"

            print(f"[Assembler] Project zipped → {zip_path}")
            print(f"[Assembler] Download URL: {download_url}")

            # Emit success event
            await self.bus.publish({
                "type": "forge_complete",
                "sender": self.name,
                "payload": {
                    "status": "success",
                    "message": f"✅ Project '{project_name}' is ready!",
                    "project_name": project_name,
                    "download_url": download_url,
                    "project_path": project_dir,
                    "user_id": user_id,
                }
            })

        except Exception as e:
            print(f"[Assembler] ZIP failed: {e}")

            await self.bus.publish({
                "type": "forge_complete",
                "sender": self.name,
                "payload": {
                    "status": "error",
                    "message": "Failed to package project",
                    "user_id": user_id,
                }
            })

    # ─────────────────────────────────────────────
    def _write_files(self, project_dir: str, files: Dict[str, str]) -> None:
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
                print(f"[Assembler] Failed writing {rel_path}: {e}")

    # ─────────────────────────────────────────────
    def _copy_template_files(self, project_dir: str) -> None:
        template_dir = os.path.join(self.TEMPLATE_DIR_BASE, self.template_type)

        if not os.path.isdir(template_dir):
            print(f"[Assembler] No template found → skipping")
            return

        print(f"[Assembler] Copying templates from: {template_dir}")

        for item in os.listdir(template_dir):
            src = os.path.join(template_dir, item)
            dst = os.path.join(project_dir, item)

            try:
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                    print(f"[Assembler] Copied: {item}")
                elif os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                    print(f"[Assembler] Copied dir: {item}/")
            except Exception as e:
                print(f"[Assembler] Failed copying {item}: {e}")

    # ─────────────────────────────────────────────
    def _generate_readme(self, project_dir: str, task: str) -> None:
        readme_path = os.path.join(project_dir, "README.md")

        content = f"""# {task.title()}

Generated by **NOX Forge** on {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Overview
This project was automatically generated from:

> {task}

## Run Instructions

```bash
cd {os.path.basename(project_dir)}

python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\\Scripts\\activate       # Windows

pip install -r requirements.txt

python main.py
"""