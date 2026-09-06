"""Main CLI Entrypoint for AgentForge."""

from __future__ import annotations

import typer
from rich.console import Console

from agentforge.cli.commands.build import build_command
from agentforge.cli.commands.deploy import deploy_command
from agentforge.cli.commands.dev import dev_command
from agentforge.cli.commands.new import new_command

console = Console()

app = typer.Typer(
    name="agentforge",
    help="⚡ Fast, Standalone & Production-Ready AI Agent Scaffolding Framework",
    add_completion=False,
    no_args_is_help=True,
)

# Register subcommands
app.command(name="new", help="Scaffold a new standalone AI agent project")(new_command)
app.command(name="dev", help="Run local development servers (Backend + Frontend)")(dev_command)
app.command(name="build", help="Build Docker container images")(build_command)
app.command(name="deploy", help="Deploy project to Kubernetes cluster")(deploy_command)


def main() -> None:
    """Entrypoint function for CLI executable."""
    app()


if __name__ == "__main__":
    main()
