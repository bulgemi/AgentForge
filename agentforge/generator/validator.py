"""Validation utilities for AgentForge project generation and scaffolding."""

from __future__ import annotations

import compileall
import os
import re
import sys
from pathlib import Path
from typing import Sequence

SUPPORTED_FRAMEWORKS = (
    "langchain",
    "langgraph",
    "deepagent",
    "adk",
    "bedrock",
    "llamaindex",
    "google_genai",
    "crewai",
    "autogen",
)

SUPPORTED_FRONTENDS = ("react", "react-vite", "streamlit", "none")


class ValidationError(Exception):
    """Raised when project validation fails."""


def validate_project_name(name: str) -> str:
    """Validate project identifier.
    
    Must consist of alphanumeric characters, underscores, or hyphens,
    and must contain at least one alphanumeric character.
    """
    cleaned = name.strip()
    if not cleaned:
        raise ValidationError("Project name cannot be empty.")
    if not re.match(r"^[a-zA-Z0-9_-]+$", cleaned):
        raise ValidationError(
            f"Invalid project name '{cleaned}'. Must contain only letters, numbers, hyphens, and underscores."
        )
    if not re.search(r"[a-zA-Z0-9]", cleaned):
        raise ValidationError(
            f"Invalid project name '{cleaned}'. Must contain at least one letter or digit."
        )
    return cleaned


def validate_framework(framework: str) -> str:
    """Validate and normalize agent framework name."""
    normalized = framework.strip().lower().replace("-", "_")
    if normalized == "aws_bedrock":
        normalized = "bedrock"
    if normalized not in SUPPORTED_FRAMEWORKS:
        raise ValidationError(
            f"Unsupported framework '{framework}'. Supported: {', '.join(SUPPORTED_FRAMEWORKS)}"
        )
    return normalized


def validate_frontend(frontend: str) -> str:
    """Validate and normalize frontend UI choice."""
    normalized = frontend.strip().lower().replace("-", "_")
    if normalized in ("react", "react_vite", "vite"):
        return "react-vite"
    if normalized == "streamlit":
        return "streamlit"
    if normalized in ("none", "headless", "api_only"):
        return "none"
    raise ValidationError(
        f"Unsupported frontend '{frontend}'. Supported: react, streamlit, none"
    )


def validate_target_directory(path: str | Path, force: bool = False) -> Path:
    """Validate that target directory can be created or is safely reusable."""
    target = Path(path).resolve()
    if target.exists() and not force:
        # Check if non-empty
        if any(target.iterdir()):
            raise ValidationError(
                f"Target directory '{target}' already exists and is not empty. Use --force to overwrite."
            )
    return target


def validate_generated_project(project_path: str | Path) -> bool:
    """Perform post-scaffold integrity and syntax checks on generated python code."""
    path = Path(project_path).resolve()
    if not path.exists():
        raise ValidationError(f"Project directory '{path}' does not exist.")

    backend_src = path / "backend" / "src"
    if backend_src.exists():
        success = compileall.compile_dir(str(backend_src), quiet=1, force=False)
        if not success:
            raise ValidationError(
                f"Syntax validation failed for generated python files in {backend_src}"
            )
    return True
