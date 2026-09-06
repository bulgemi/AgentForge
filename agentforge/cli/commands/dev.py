"""CLI command for running local development servers."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

console = Console()


def dev_command(
    port: int = typer.Option(8000, "--port", "-p", help="Backend API port"),
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Backend API host"),
    frontend_port: int = typer.Option(5173, "--ui-port", help="Frontend port"),
    reload: bool = typer.Option(True, "--reload/--no-reload", help="Auto-reload backend"),
) -> None:
    """Run local development environment (FastAPI Backend + Vite Frontend)."""
    current_dir = Path.cwd()
    backend_dir = current_dir / "backend"
    frontend_dir = current_dir / "frontend"

    if not backend_dir.exists():
        console.print("[bold red]Error:[/bold red] 'backend' directory not found in current directory.")
        console.print("Please run this command from the root of an AgentForge project.")
        raise typer.Exit(code=1)

    console.print("[bold cyan]⚡ Starting AgentForge Development Environment[/bold cyan]")
    console.print(f"• Backend API: [bold green]http://{host}:{port}[/bold green] (Docs: http://{host}:{port}/docs)")
    if frontend_dir.exists():
        console.print(f"• Frontend UI: [bold green]http://localhost:{frontend_port}[/bold green]")
        console.print(f"• Admin UI:    [bold green]http://localhost:{frontend_port}/admin/[/bold green]\n")

    # Launch Backend with uvicorn via subprocess
    backend_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "src.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    if reload:
        backend_cmd.append("--reload")

    console.print("[dim]Starting backend uvicorn server... (Press Ctrl+C to stop)[/dim]")
    try:
        proc = subprocess.run(backend_cmd, cwd=str(backend_dir))
        sys.exit(proc.returncode)
    except KeyboardInterrupt:
        console.print("\n[yellow]Development server stopped.[/yellow]")
