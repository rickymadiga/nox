import os
import datetime
import shutil
import io
import zipfile
from typing import Dict

from ..core.agent import Agent
from ..core.message import Message


class Assembler(Agent):
    """
    Final pipeline stage: Assembles approved code into a proper project folder,
    creates both on-disk zip and in-memory zip bytes, then emits download info.
    """

    OUTPUT_BASE_DIR = "generated_apps"
    TEMPLATE_DIR_BASE = "forge/templates"

    def __init__(self, runtime):
        # Updated to match new runtime style
        self.runtime = runtime
        self.bus = runtime.bus
        self.name = "assembler"
        self.template_type = "default"

        # Subscribe to CODE_APPROVED
        self.bus.subscribe("CODE_APPROVED", self.on_code_approved)

        print("[Assembler] Initialized and subscribed to CODE_APPROVED")

    def register(self) -> None:
        print("[Assembler] Registered")

    # ─────────────────────────────────────────────
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

        # ─────────────────────────────────────────
        # Create unique project directory
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

        # 1. Write generated files
        self._write_files(project_dir, files)

        # 2. Copy template files
        self._copy_template_files(project_dir)

        # 3. Generate README
        self._generate_readme(project_dir, task)

        print("\n" + "=" * 50)
        print(" BUILD COMPLETE ".center(50))
        print(f" Project     : {project_name}")
        print(f" Location    : {project_dir}")
        print("=" * 50 + "\n")

        # ─────────────────────────────────────────
        # ZIP PROJECT - BULLETPROOF VERSION
        try:
            print(f"[Assembler] Creating ZIP packages for {project_name}...")

            # 1. On-disk ZIP (reliable)
            zip_base = os.path.join(self.OUTPUT_BASE_DIR, project_name)
            zip_path = shutil.make_archive(zip_base, 'zip', root_dir=project_dir)
            download_url = f"/download/{project_name}"

            print(f"[Assembler] On-disk ZIP created → {zip_path}")

            # 2. In-memory ZIP - Bulletproof
            zip_buffer = io.BytesIO()

            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files_in_dir in os.walk(project_dir):
                    for filename in files_in_dir:
                        full_path = os.path.join(root, filename)

                        if not os.path.isfile(full_path):
                            continue

                        # Correct relative path for the zip
                        arcname = os.path.relpath(full_path, project_dir)

                        print(f"[Assembler] Adding to ZIP: {arcname}")  # Debug - you can remove later

                        try:
                            zf.write(full_path, arcname)
                        except Exception as e:
                            print(f"[Assembler] Failed to add {arcname}: {e}")

            zip_buffer.seek(0)
            zip_bytes = zip_buffer.getvalue()   # ← Use getvalue(), not read()

            print(f"[Assembler] In-memory ZIP created: {len(zip_bytes)} bytes ({len(zip_bytes) // 1024} KB)")

            # Store for runtime / download
            self.runtime.last_zip = {
                "bytes": zip_bytes,
                "filename": f"{project_name}.zip"
            }

            # Publish completion
            await self.bus.publish(
                Message(
                    sender=self.name,
                    recipient="arena",
                    message_type="forge_complete",
                    payload={
                        "status": "success",
                        "message": f"✅ Project '{project_name}' is ready!",
                        "project_name": project_name,
                        "download_url": download_url,
                        "zip_bytes": zip_bytes,
                        "filename": f"{project_name}.zip",
                        "user_id": user_id,
                    }
                )
            )

        except Exception as e:
            print(f"[Assembler] ZIP creation failed: {e}")
            await self.bus.publish(
                Message(
                    sender=self.name,
                    recipient="arena",
                    message_type="forge_complete",
                    payload={
                        "status": "error",
                        "message": f"Failed to package project: {e}",
                        "user_id": user_id,
                    }
                )
            )

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