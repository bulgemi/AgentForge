"""CLI command for creating new standalone agent projects."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from agentforge.generator.engine import ScaffoldingEngine
from agentforge.generator.validator import (
    SUPPORTED_FRAMEWORKS,
    SUPPORTED_FRONTENDS,
    ValidationError,
)

console = Console()


def new_command(
    name: str = typer.Argument(..., help="Name of the new agent project"),
    framework: str = typer.Option(
        "langgraph",
        "--framework",
        "-f",
        help=f"Agent framework: {', '.join(SUPPORTED_FRAMEWORKS)}",
    ),
    frontend: str = typer.Option(
        "react",
        "--frontend",
        "-ui",
        help="Frontend interface: react (Vite), streamlit, none",
    ),
    path: str = typer.Option(
        ".",
        "--path",
        "-p",
        help="Target directory path where project will be created",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite target directory if it already exists",
    ),
) -> None:
    """Scaffold a new standalone, production-ready AI agent project."""
    console.print(f"\n[bold cyan]⚡ AgentForge Project Scaffolding[/bold cyan]")
    console.print(f"Creating project [bold green]'{name}'[/bold green] at [yellow]'{path}'[/yellow]...\n")

    try:
        engine = ScaffoldingEngine()
        created_path = engine.generate(
            project_name=name,
            target_dir=path,
            framework=framework,
            frontend=frontend,
            force=force,
        )

        success_msg = f"""[bold green]✓ Project successfully generated![/bold green]

• Location:  [cyan]{created_path}[/cyan]
• Framework: [magenta]{framework}[/magenta]
• Frontend:  [yellow]{frontend}[/yellow]
• Core:      [blue]Copied standalone runtime (backend/src/core/)[/blue]

[bold]Next Steps:[/bold]
  [dim]$[/dim] cd {created_path.name}
  [dim]$[/dim] agentforge dev
"""
        console.print(Panel(success_msg, title="[bold]Ready to Build[/bold]", border_style="green"))

    except ValidationError as e:
        console.print(f"[bold red]Validation Error:[/bold red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]Error generating project:[/bold red] {e}")
        raise typer.Exit(code=1)
