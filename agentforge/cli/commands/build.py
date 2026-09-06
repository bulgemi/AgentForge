"""CLI command for building production Docker images."""

from __future__ import annotations

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
    backend_dir = current_dir / "backend"
    frontend_dir = current_dir / "frontend"

    console.print(f"[bold cyan]⚡ Building Docker Images (Tag: {tag})[/bold cyan]\n")

    if target in ("backend", "all") and backend_dir.exists():
        console.print("[bold blue]Building backend image...[/bold blue]")
        cmd = ["docker", "build", "-t", f"agent-backend:{tag}", "-f", "Dockerfile", "."]
        res = subprocess.run(cmd, cwd=str(backend_dir))
        if res.returncode != 0:
            console.print("[bold red]Failed to build backend image.[/bold red]")
            raise typer.Exit(code=res.returncode)

    if target in ("frontend", "all") and frontend_dir.exists():
        console.print("[bold blue]Building frontend image...[/bold blue]")
        dockerfile = frontend_dir / "docker" / "Dockerfile"
        if not dockerfile.exists():
            dockerfile = frontend_dir / "Dockerfile"
        cmd = ["docker", "build", "-t", f"agent-frontend:{tag}", "-f", str(dockerfile), "."]
        res = subprocess.run(cmd, cwd=str(frontend_dir))
        if res.returncode != 0:
            console.print("[bold red]Failed to build frontend image.[/bold red]")
            raise typer.Exit(code=res.returncode)

    console.print(f"\n[bold green]✓ Docker build completed successfully![/bold green]")
