"""CLI command for building production Docker images."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console

console = Console()


def build_command(
    tag: str = typer.Option("latest", "--tag", "-t", help="Docker image tag"),
    target: str = typer.Option("all", "--target", help="Build target: backend, frontend, all"),
) -> None:
    """Build production container images for Backend and Frontend."""
    current_dir = Path.cwd()
    project_name = current_dir.name or "agent"
    clean_name = re.sub(r"[^a-z0-9-]", "-", project_name.lower()).strip("-")
    backend_dir = current_dir / "backend"
    frontend_dir = current_dir / "frontend"

    console.print(f"[bold cyan]⚡ Building Docker Images (Tag: {tag}, Project: {project_name})[/bold cyan]\n")

    if target in ("backend", "all") and backend_dir.exists():
        console.print("[bold blue]Building backend image...[/bold blue]")
        cmd = ["docker", "build", "-t", f"{project_name}-backend:{tag}"]
        if clean_name and clean_name != project_name:
            cmd.extend(["-t", f"{clean_name}-backend:{tag}"])
        cmd.extend(["-t", f"agent-backend:{tag}", "-f", "Dockerfile", "."])
        res = subprocess.run(cmd, cwd=str(backend_dir))
        if res.returncode != 0:
            console.print("[bold red]Failed to build backend image.[/bold red]")
            raise typer.Exit(code=res.returncode)

    if target in ("frontend", "all") and frontend_dir.exists():
        console.print("[bold blue]Building frontend image...[/bold blue]")
        dockerfile = frontend_dir / "docker" / "Dockerfile"
        if not dockerfile.exists():
            dockerfile = frontend_dir / "Dockerfile"
        cmd = ["docker", "build", "-t", f"{project_name}-frontend:{tag}"]
        if clean_name and clean_name != project_name:
            cmd.extend(["-t", f"{clean_name}-frontend:{tag}"])
        cmd.extend(["-t", f"agent-frontend:{tag}", "-f", str(dockerfile), "."])
        res = subprocess.run(cmd, cwd=str(frontend_dir))
        if res.returncode != 0:
            console.print("[bold red]Failed to build frontend image.[/bold red]")
            raise typer.Exit(code=res.returncode)

    console.print(f"\n[bold green]✓ Docker build completed successfully![/bold green]")

