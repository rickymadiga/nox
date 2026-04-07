import os
import datetime
import shutil
import io
import zipfile
from typing import Any, Dict

from ..core.agent import Agent
from ..core.message import Message


class Assembler(Agent):
    OUTPUT_BASE_DIR = "generated_apps"
    TEMPLATE_DIR_BASE = "forge/templates"

    def __init__(self, name: str, bus: Any, context: dict) -> None:
        super().__init__(name=name, bus=bus, context=context)
        self.template_type = "default"

        # fallback context storage
        if isinstance(context, dict):
            context.setdefault("last_zip", {})

    def register(self) -> None:
        print("[Assembler] Subscribing to CODE_APPROVED")
        self.bus.subscribe("CODE_APPROVED", self.handle)

    async def handle(self, message: Message) -> None:
        if message.message_type != "CODE_APPROVED":
            return

        payload = message.payload or {}

        files: Dict[str, str] = payload.get("files", {})
        task: str = payload.get("task", "generated_app").strip()
        user_id: str = payload.get("user_id", "default_user")

        if not files:
            print("[Assembler] No files received → skipping")
            return

        # ─────────────────────────────
        # CREATE PROJECT
        # ─────────────────────────────
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

        print(f"[Assembler] Creating project: {project_name}")

        self._write_files(project_dir, files)
        self._copy_template_files(project_dir)
        self._generate_readme(project_dir, task)

        # ─────────────────────────────
        # CREATE ZIP
        # ─────────────────────────────
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, filenames in os.walk(project_dir):
                for filename in filenames:
                    full_path = os.path.join(root, filename)
                    arcname = os.path.relpath(full_path, project_dir)
                    zf.write(full_path, arcname)

        zip_buffer.seek(0)
        zip_bytes = zip_buffer.getvalue()

        print(f"[Assembler] ZIP ready: {len(zip_bytes):,} bytes")

        # ─────────────────────────────
        # SAVE ZIP TO DISK (IMPORTANT)
        # ─────────────────────────────
        zip_path = os.path.join(self.OUTPUT_BASE_DIR, f"{project_name}.zip")
        try:
            with open(zip_path, "wb") as f:
                f.write(zip_bytes)
            print(f"[Assembler] Saved ZIP to disk: {zip_path}")
        except Exception as e:
            print(f"[Assembler] Failed saving ZIP to disk: {e}")

        # ─────────────────────────────
        # STORE ZIP IN RUNTIME (CRITICAL FIX)
        # ─────────────────────────────
        try:
            runtime = self.context.get("runtime")

            if runtime:
                if not hasattr(runtime, "last_zip") or not isinstance(runtime.last_zip, dict):
                    runtime.last_zip = {}

                runtime.last_zip[user_id] = {
                    "bytes": zip_bytes,
                    "filename": f"{project_name}.zip",
                }

                print(f"[Assembler] Stored ZIP in runtime for {user_id}")

            # fallback (optional)
            if isinstance(self.context, dict):
                self.context.setdefault("last_zip", {})
                self.context["last_zip"][user_id] = {
                    "bytes": zip_bytes,
                    "filename": f"{project_name}.zip",
                }

        except Exception as e:
            print(f"[Assembler] Failed storing ZIP: {e}")

        # ─────────────────────────────
        # NOTIFY LILY
        # ─────────────────────────────
        await self.bus.publish(
            Message(
                sender="assembler",
                recipient="lily",
                message_type="forge_complete",
                payload={
                    "user_id": user_id,
                    "project_name": project_name,
                    "result": {
                        "bytes": zip_bytes,
                        "filename": f"{project_name}.zip",
                    },
                },
            )
        )

        print(f"[Assembler] ✅ Build complete → {project_name}")

    # ─────────────────────────────
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

    def _copy_template_files(self, project_dir: str) -> None:
        template_dir = os.path.join(self.TEMPLATE_DIR_BASE, self.template_type)

        if not os.path.isdir(template_dir):
            print("[Assembler] No template → skipping")
            return

        for item in os.listdir(template_dir):
            src = os.path.join(template_dir, item)
            dst = os.path.join(project_dir, item)

            try:
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                elif os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
            except Exception as e:
                print(f"[Assembler] Template error: {e}")

    def _generate_readme(self, project_dir: str, task: str) -> None:
        readme_path = os.path.join(project_dir, "README.md")

        content = (
            f"# {task}\n\n"
            f"Generated by Forge on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "## How to Run\n\n"
            f"cd {os.path.basename(project_dir)}\n"
            "python -m venv .venv\n"
            "source .venv/bin/activate  # or Windows equivalent\n"
            "pip install -r requirements.txt\n"
            "python main.py\n"
        )

        try:
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(content)
            print("[Assembler] Generated README.md")
        except Exception as e:
            print(f"[Assembler] Failed to generate README: {e}")