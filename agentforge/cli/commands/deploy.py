"""CLI command for Kubernetes deployment."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console

console = Console()


def deploy_command(
    environment: str = typer.Option("dev", "--env", "-e", help="Target environment: dev or prd"),
    namespace: str = typer.Option("ai-agents", "--namespace", "-n", help="Kubernetes namespace"),
) -> None:
    """Deploy the project to Kubernetes cluster using k8s manifests."""
    current_dir = Path.cwd()
    deploy_script = current_dir / "k8s" / "k8s-deploy.sh"

    if not deploy_script.exists():
        console.print(f"[bold red]Error:[/bold red] Deployment script '{deploy_script}' not found.")
        raise typer.Exit(code=1)

    console.print(f"[bold cyan]⚡ Deploying AgentForge Project to Kubernetes[/bold cyan]")
    console.print(f"• Environment: [bold yellow]{environment}[/bold yellow]")
    console.print(f"• Namespace:   [bold yellow]{namespace}[/bold yellow]\n")

    cmd = ["bash", str(deploy_script), environment, namespace]
    res = subprocess.run(cmd, cwd=str(current_dir))
    if res.returncode != 0:
        console.print("[bold red]Deployment failed.[/bold red]")
        raise typer.Exit(code=res.returncode)

    console.print("\n[bold green]✓ Deployment completed successfully![/bold green]")
