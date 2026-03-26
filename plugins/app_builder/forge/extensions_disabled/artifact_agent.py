# forge/extensions/artifact_agent.py
"""
ArtifactAgent – Collects, organizes and saves final build artifacts (code, docs, tests, configs, etc.).
This is an optional extension – can be enabled via config or CLI flag.
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class ArtifactAgent:
    """
    Manages saving of final artifacts to a structured build folder.
    Phase 1: simple file/directory write – no zipping or versioning yet.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.base_output_dir = Path(self.config.get(
            "output_dir",
            "builds"
        ))
        self.build_timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        self.build_id = self.config.get("build_id", f"build-{self.build_timestamp}")
        self.build_dir = self.base_output_dir / self.build_id
        self.build_dir.mkdir(parents=True, exist_ok=True)

    def save_file(
        self,
        filename: str,
        content: str | bytes,
        subfolder: Optional[str] = None
    ) -> Path:
        """
        Save a single artifact file to the build folder.
        
        Args:
            filename: e.g. "main.py", "README.md", "tests/test_main.py"
            content: string or bytes to write
            subfolder: optional subdir inside build folder (e.g. "src", "tests")
        
        Returns:
            Path: full path where file was saved
        """
        target_dir = self.build_dir
        if subfolder:
            target_dir = target_dir / subfolder
            target_dir.mkdir(parents=True, exist_ok=True)

        target_path = target_dir / filename

        try:
            if isinstance(content, bytes):
                target_path.write_bytes(content)
            else:
                target_path.write_text(content, encoding="utf-8")
            print(f"[ArtifactAgent] Saved: {target_path}")
            return target_path
        except Exception as e:
            print(f"[ArtifactAgent ERROR] Failed to save {filename}: {str(e)}")
            raise

    def save_multiple(
        self,
        artifacts: List[Dict[str, Any]]
    ) -> List[Path]:
        """
        Save multiple artifacts at once.
        
        Each item in artifacts should be:
        {"filename": str, "content": str|bytes, "subfolder": str (optional)}
        """
        saved_paths = []
        for art in artifacts:
            path = self.save_file(
                filename=art["filename"],
                content=art["content"],
                subfolder=art.get("subfolder")
            )
            saved_paths.append(path)
        return saved_paths

    def get_build_path(self) -> Path:
        """Return the current build directory path."""
        return self.build_dir

    # Future: add zip packaging, git commit, dockerfile generation, version bumping, etc.