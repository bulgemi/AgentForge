"""Copier module to transfer AgentForge core engine into target standalone projects."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Sequence

# Locate the root core directory within agentforge package
PACKAGE_CORE_DIR = Path(__file__).resolve().parent.parent / "core"


def copy_core_engine(
    destination_backend_src: str | Path,
    source_core_dir: str | Path | None = None,
    overwrite: bool = True,
) -> list[Path]:
    """Copy the AgentForge core engine into backend/src/core/ of the generated project.

    Args:
        destination_backend_src: Path to the generated project's backend/src directory.
        source_core_dir: Optional source directory override (defaults to agentforge/core).
        overwrite: Whether to overwrite existing files in destination.

    Returns:
        List of copied file Paths.
    """
    src_dir = Path(source_core_dir or PACKAGE_CORE_DIR).resolve()
    if not src_dir.exists():
        raise FileNotFoundError(f"Source core directory '{src_dir}' does not exist.")

    dest_dir = Path(destination_backend_src).resolve() / "core"
    dest_dir.mkdir(parents=True, exist_ok=True)

    copied_files: list[Path] = []

    for item in src_dir.iterdir():
        if item.name.startswith("__pycache__") or item.suffix in (".pyc", ".pyo"):
            continue
        if item.is_file() and item.suffix == ".py":
            target_file = dest_dir / item.name
            if target_file.exists() and not overwrite:
                continue
            shutil.copy2(item, target_file)
            copied_files.append(target_file)
        elif item.is_dir() and not item.name.startswith("."):
            target_subdir = dest_dir / item.name
            target_subdir.mkdir(parents=True, exist_ok=True)
            for sub_item in item.glob("**/*.py"):
                rel_path = sub_item.relative_to(item)
                sub_target = target_subdir / rel_path
                sub_target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(sub_item, sub_target)
                copied_files.append(sub_target)

    # Ensure __init__.py exists in copied core
    init_file = dest_dir / "__init__.py"
    if not init_file.exists():
        init_file.touch()
        copied_files.append(init_file)

    return copied_files
