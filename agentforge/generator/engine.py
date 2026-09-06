"""Scaffolding and template synthesis engine for AgentForge projects."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Mapping

from .copier import copy_core_engine
from .validator import (
    ValidationError,
    validate_framework,
    validate_frontend,
    validate_generated_project,
    validate_project_name,
    validate_target_directory,
)

PACKAGE_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
PACKAGE_ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets"


class ScaffoldingEngine:
    """Orchestrates creation of fullstack standalone agent projects."""

    def __init__(self, templates_dir: str | Path | None = None) -> None:
        self.templates_dir = Path(templates_dir or PACKAGE_TEMPLATES_DIR).resolve()

    def render_content(self, text: str, context: Mapping[str, Any]) -> str:
        """Simple, fast token replacement without requiring heavy template runtime."""
        rendered = text
        for key, value in context.items():
            token_bracket = "{{" + f" {key} " + "}}"
            token_compact = "{{" + f"{key}" + "}}"
            rendered = rendered.replace(token_bracket, str(value))
            rendered = rendered.replace(token_compact, str(value))
        return rendered

    def copy_template_tree(
        self,
        source_dir: Path,
        dest_dir: Path,
        context: Mapping[str, Any],
        exclude_exts: tuple[str, ...] = (".pyc", ".pyo"),
    ) -> None:
        """Recursively copy template directory tree, substituting variables in text files."""
        if not source_dir.exists():
            return

        dest_dir.mkdir(parents=True, exist_ok=True)
        text_extensions = (
            ".py",
            ".json",
            ".yaml",
            ".yml",
            ".md",
            ".toml",
            ".js",
            ".jsx",
            ".ts",
            ".tsx",
            ".html",
            ".css",
            ".sh",
            ".env",
            ".sample",
            ".ini",
            ".conf",
            ".txt",
        )

        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if not d.startswith("__pycache__") and d != "node_modules"]
            rel_dir = Path(root).relative_to(source_dir)
            target_current_dir = dest_dir / rel_dir
            target_current_dir.mkdir(parents=True, exist_ok=True)

            for file_name in files:
                if any(file_name.endswith(ext) for ext in exclude_exts):
                    continue
                src_file = Path(root) / file_name
                dest_file = target_current_dir / file_name

                # Check if it is a text template that can be substituted
                is_text = any(file_name.endswith(ext) for ext in text_extensions) or file_name.startswith(".env")
                if is_text:
                    try:
                        content = src_file.read_text(encoding="utf-8")
                        rendered = self.render_content(content, context)
                        dest_file.write_text(rendered, encoding="utf-8")
                        # Preserve executable permissions for scripts
                        if src_file.stat().st_mode & 0o111:
                            dest_file.chmod(dest_file.stat().st_mode | 0o111)
                        continue
                    except UnicodeDecodeError:
                        pass

                # Binary or non-text file copy
                shutil.copy2(src_file, dest_file)

    def generate(
        self,
        project_name: str,
        target_dir: str | Path,
        framework: str = "langgraph",
        frontend: str = "react-vite",
        force: bool = False,
    ) -> Path:
        """Generate a complete standalone project with backend, frontend, infra, and core.

        Args:
            project_name: Name of the project.
            target_dir: Directory where the project should be created.
            framework: Agent framework (e.g. langgraph, langchain, bedrock, etc.).
            frontend: Frontend framework (react-vite, streamlit, or none).
            force: Overwrite if directory exists.

        Returns:
            Path to the created project.
        """
        clean_name = validate_project_name(project_name)
        clean_framework = validate_framework(framework)
        clean_frontend = validate_frontend(frontend)
        dest_root = validate_target_directory(Path(target_dir) / clean_name, force=force)
        dest_root.mkdir(parents=True, exist_ok=True)

        context = {
            "project_name": clean_name,
            "project_name_snake": clean_name.replace("-", "_"),
            "framework": clean_framework,
            "frontend": clean_frontend,
            "python_version": "3.11",
        }

        # 1. Copy Backend Template
        backend_tpl = self.templates_dir / "backend"
        if backend_tpl.exists():
            self.copy_template_tree(backend_tpl, dest_root / "backend", context)

        # 2. Inject Selected Framework Adapter Template
        framework_tpl = self.templates_dir / "backend" / "src" / "frameworks" / clean_framework
        if framework_tpl.exists():
            dest_fw = dest_root / "backend" / "src" / "infrastructure" / "adapters" / "agent"
            dest_fw.mkdir(parents=True, exist_ok=True)
            self.copy_template_tree(framework_tpl, dest_fw, context)

        # 3. Copy Frontend Template
        if clean_frontend in ("react", "react-vite"):
            frontend_tpl = self.templates_dir / "frontend" / "react-vite"
            if frontend_tpl.exists():
                self.copy_template_tree(frontend_tpl, dest_root / "frontend", context)

            # Ensure branding assets (favicon, logos) from assets/ are synced to frontend/public
            if PACKAGE_ASSETS_DIR.exists():
                dest_public = dest_root / "frontend" / "public"
                dest_public.mkdir(parents=True, exist_ok=True)
                for asset_file in PACKAGE_ASSETS_DIR.iterdir():
                    if asset_file.is_file() and not asset_file.name.startswith("."):
                        shutil.copy2(asset_file, dest_public / asset_file.name)
        elif clean_frontend == "streamlit":
            streamlit_tpl = self.templates_dir / "frontend" / "streamlit"
            if streamlit_tpl.exists():
                self.copy_template_tree(streamlit_tpl, dest_root / "frontend", context)

        # 4. Copy Infrastructure & Kubernetes Templates
        infra_tpl = self.templates_dir / "infra"
        if infra_tpl.exists():
            # docker-compose.yml and postgres-init
            for item in infra_tpl.iterdir():
                if item.is_file():
                    content = item.read_text(encoding="utf-8")
                    (dest_root / item.name).write_text(self.render_content(content, context), encoding="utf-8")
                elif item.is_dir():
                    self.copy_template_tree(item, dest_root / item.name, context)

        k8s_tpl = self.templates_dir / "k8s"
        if k8s_tpl.exists():
            self.copy_template_tree(k8s_tpl, dest_root / "k8s", context)

        # 4.1 Copy Convenience Scripts (run.sh, run.bat, setup.sh, setup.bat)
        scripts_tpl = self.templates_dir / "scripts"
        if scripts_tpl.exists():
            for item in scripts_tpl.iterdir():
                if item.is_file():
                    content = item.read_text(encoding="utf-8")
                    dest_file = dest_root / item.name
                    dest_file.write_text(self.render_content(content, context), encoding="utf-8")
                    if item.name.endswith(".sh"):
                        dest_file.chmod(dest_file.stat().st_mode | 0o755)

        # 5. Standalone Core Engine Copy
        dest_backend_src = dest_root / "backend" / "src"
        copy_core_engine(dest_backend_src, overwrite=True)

        # 6. Generate project README.md and root files
        readme_path = dest_root / "README.md"
        if not readme_path.exists():
            readme_content = f"""# {clean_name} ⚡

Standalone AI Agent Project built with [AgentForge](https://github.com/bulgemi/AgentForge).

- **Framework**: {clean_framework}
- **Frontend**: {clean_frontend}
- **Architecture**: Fullstack Clean Architecture Monorepo
- **Authentication**: ID/PW, LDAP, SAML 2.0
- **Database**: PostgreSQL 16 + Redis 7

## Quick Start

### 1. One-Click Local Run (Recommended)
Automatically sets up virtual environment, installs dependencies, and runs dev servers.

```bash
# macOS / Linux
./run.sh

# Windows
run.bat
```

> **Tip**: To install dependencies only without starting servers, run `./setup.sh` or `setup.bat`.

### 2. Run with Docker Compose
```bash
docker-compose up -d
```
- Frontend (Chat): http://localhost:5173
- Frontend (Admin): http://localhost:5173/admin/
- Backend API Docs: http://localhost:8000/docs

### 3. Manual Run Locally
```bash
# Backend
cd backend
uv run uvicorn src.main:app --reload --port 8000

# Frontend
cd ../frontend
npm install
npm run dev
```
"""
            readme_path.write_text(readme_content, encoding="utf-8")

        # 7. Post-scaffold syntax verification
        validate_generated_project(dest_root)

        return dest_root
