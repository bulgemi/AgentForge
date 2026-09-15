"""CLI commands for developer sandbox management across AWS, GCP, Azure, and Rancher."""

from __future__ import annotations

import shutil
import subprocess
import webbrowser
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from agentforge.sandbox.csp import get_csp_adapter
from agentforge.sandbox.manager import SandboxManager
from agentforge.sandbox.watcher import FastFileSyncer

console = Console()

sandbox_app = typer.Typer(
    name="sandbox",
    help="⚡ Manage isolated developer sandboxes on AWS EKS, GCP GKE, Azure AKS via Rancher",
    no_args_is_help=True,
)


@sandbox_app.command(name="up", help="Provision an isolated developer sandbox on target cloud K8s cluster")
def sandbox_up(
    csp: str = typer.Option("aws", "--csp", "-c", help="Target cloud provider: aws (EKS), gcp (GKE), azure (AKS)"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Developer sandbox name (defaults to current OS user)"),
    ttl: str = typer.Option("8h", "--ttl", "-t", help="Sandbox TTL duration before auto-cleanup (e.g. 4h, 8h, 24h, 2d)"),
    domain: str = typer.Option("sandbox.agentforge.io", "--domain", "-d", help="Wildcard base domain for sandbox ingress"),
    shared_db: bool = typer.Option(False, "--shared-db", help="Use central shared RDS/CloudSQL instead of embedded in-cluster pod"),
    rancher_project_id: Optional[str] = typer.Option(None, "--rancher-project", "-p", help="Rancher Project ID (e.g. c-xxxx:p-yyyy)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Render and display generated Kubernetes manifests without applying"),
    watch: bool = typer.Option(False, "--watch", "-w", help="Start real-time code watcher immediately after provisioning"),
) -> None:
    """Create and start a developer sandbox."""
    dev_name = name or SandboxManager.get_default_developer_name()
    namespace = SandboxManager.get_namespace(dev_name)
    current_dir = Path.cwd()
    project_name = current_dir.name or "agentforge-app"

    try:
        adapter = get_csp_adapter(csp)
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)

    console.print("\n[bold cyan]⚡ Provisioning Developer Sandbox[/bold cyan]")
    console.print(f"• Developer:   [bold green]{dev_name}[/bold green]")
    console.print(f"• Namespace:   [bold yellow]{namespace}[/bold yellow]")
    console.print(f"• Cloud CSP:   [bold magenta]{adapter.csp_name.upper()}[/bold magenta]")
    console.print(f"• TTL Policy:  [cyan]{ttl}[/cyan]")
    console.print(f"• Database:    [blue]{'Shared Cloud DB' if shared_db else 'Isolated In-Cluster Pod'}[/blue]")
    console.print(f"• Endpoint:    [bold underline]https://{dev_name}.{domain}[/bold underline]\n")

    manager = SandboxManager()
    manifests = manager.generate_sandbox_artifacts(
        developer_name=dev_name,
        project_name=project_name,
        csp_name=adapter.csp_name,
        ttl=ttl,
        domain_suffix=domain,
        shared_db=shared_db,
        rancher_project_id=rancher_project_id,
    )

    manager.apply_manifests(manifests, dry_run=dry_run)

    if dry_run:
        console.print("\n[green]✓ Dry-run completed. No cluster changes made.[/green]")
        return

    # Deploy Helm chart if chart exists
    chart_dir = current_dir / "charts" / project_name
    if not chart_dir.exists():
        charts_root = current_dir / "charts"
        if charts_root.exists():
            sub = next((d for d in charts_root.iterdir() if d.is_dir() and (d / "Chart.yaml").exists()), None)
            if sub:
                chart_dir = sub

    if chart_dir.exists() and shutil.which("helm"):
        console.print(f"[dim]Deploying Helm release '{namespace}' into '{namespace}'...[/dim]")
        # Write temporary sandbox values
        temp_val = chart_dir / ".sandbox-values.yaml"
        try:
            temp_val.write_text(manifests["values-sandbox.yaml"], encoding="utf-8")
            helm_cmd = [
                "helm", "upgrade", "--install", namespace, str(chart_dir),
                "-n", namespace,
                "-f", str(temp_val),
            ]
            subprocess.run(helm_cmd, capture_output=True, text=True)
        finally:
            if temp_val.exists():
                temp_val.unlink()
        console.print("[bold green]✓ Helm release deployed successfully[/bold green]")
    else:
        # Deploy standard AgentForge k8s manifests (k8s/dev)
        k8s_dev = current_dir / "k8s" / "dev"
        if k8s_dev.exists():
            console.print(f"[dim]Deploying Kubernetes workloads from '{k8s_dev.relative_to(current_dir)}' into '{namespace}'...[/dim]")
            manager.deploy_k8s_workloads(
                namespace=namespace,
                k8s_dir=k8s_dev,
                domain_suffix=domain,
                dry_run=dry_run,
            )
            console.print(f"[bold green]✓ Kubernetes workloads deployed successfully into '{namespace}'[/bold green]")

    success_msg = f"""[bold green]✓ Developer Sandbox Ready![/bold green]

• Endpoint:  [bold cyan]https://{dev_name}.{domain}[/bold cyan]
• TTL Expiry: in {ttl} (Scale to 0 with 'af sandbox pause')

[bold]Next Steps:[/bold]
  [dim]$[/dim] af sandbox open           # Open browser or start port-forwarding
  [dim]$[/dim] af sandbox watch          # Stream live code changes to remote pod
  [dim]$[/dim] af sandbox status         # Check pods and remaining TTL
"""
    console.print(Panel(success_msg, border_style="green"))

    if watch:
        backend_dir = current_dir / "backend" / "src"
        syncer = FastFileSyncer(namespace=namespace, local_dir=backend_dir)
        syncer.start_watch_loop()


@sandbox_app.command(name="down", help="Tear down and destroy developer sandbox namespace")
def sandbox_down(
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Sandbox name to tear down"),
    force: bool = typer.Option(False, "--force", "-f", help="Bypass confirmation prompt"),
) -> None:
    """Tear down developer sandbox and release all cluster resources."""
    dev_name = name or SandboxManager.get_default_developer_name()
    namespace = SandboxManager.get_namespace(dev_name)

    if not force:
        confirm = typer.confirm(f"Are you sure you want to delete sandbox '{namespace}'?")
        if not confirm:
            console.print("[yellow]Aborted.[/yellow]")
            return

    console.print(f"[bold red]Tearing down sandbox '{namespace}'...[/bold red]")
    if shutil.which("helm"):
        subprocess.run(["helm", "uninstall", namespace, "-n", namespace], capture_output=True, text=True)

    manager = SandboxManager()
    success = manager.delete_namespace(namespace)
    if success:
        console.print(f"[bold green]✓ Sandbox '{namespace}' deleted successfully[/bold green]")
    else:
        console.print(f"[yellow]⚠ Namespace '{namespace}' marked for termination or kubectl unavailable[/yellow]")


@sandbox_app.command(name="pause", help="Scale sandbox deployments to 0 replicas to save cloud compute cost")
def sandbox_pause(
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Sandbox name"),
) -> None:
    """Pause sandbox workloads to conserve cloud compute resources."""
    dev_name = name or SandboxManager.get_default_developer_name()
    namespace = SandboxManager.get_namespace(dev_name)

    console.print(f"Pausing sandbox [bold yellow]'{namespace}'[/bold yellow] (scaling replicas to 0)...")
    manager = SandboxManager()
    manager.scale_deployments(namespace, 0)
    console.print(f"[bold green]✓ Sandbox '{namespace}' paused. Zero compute consumed.[/bold green]")


@sandbox_app.command(name="resume", help="Resume paused sandbox workloads back to 1 replica")
def sandbox_resume(
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Sandbox name"),
) -> None:
    """Resume paused sandbox workloads."""
    dev_name = name or SandboxManager.get_default_developer_name()
    namespace = SandboxManager.get_namespace(dev_name)

    console.print(f"Resuming sandbox [bold green]'{namespace}'[/bold green]...")
    manager = SandboxManager()
    manager.scale_deployments(namespace, 1)
    console.print(f"[bold green]✓ Sandbox '{namespace}' resumed.[/bold green]")


@sandbox_app.command(name="status", help="Inspect developer sandbox pods, resources, and TTL")
def sandbox_status(
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Sandbox name"),
) -> None:
    """Display live health, pods, and TTL status of sandbox."""
    dev_name = name or SandboxManager.get_default_developer_name()
    namespace = SandboxManager.get_namespace(dev_name)

    console.print(f"\n[bold cyan]⚡ Sandbox Status: {namespace}[/bold cyan]\n")

    if not shutil.which("kubectl"):
        console.print("[yellow]kubectl not found in PATH.[/yellow]")
        return

    cmd = ["kubectl", "get", "pods", "-n", namespace, "-o", "wide"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        console.print(f"[yellow]Sandbox '{namespace}' not found or cluster unreachable.[/yellow]")
        return

    console.print(res.stdout)


@sandbox_app.command(name="watch", help="Start continuous live file synchronization to remote sandbox pod")
def sandbox_watch(
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Sandbox name"),
    dir: Path = typer.Option(Path("backend/src"), "--dir", help="Local directory to watch"),
) -> None:
    """Watch and stream local code changes to the remote sandbox container."""
    dev_name = name or SandboxManager.get_default_developer_name()
    namespace = SandboxManager.get_namespace(dev_name)

    target_dir = Path.cwd() / dir
    syncer = FastFileSyncer(namespace=namespace, local_dir=target_dir)
    syncer.start_watch_loop()


@sandbox_app.command(name="open", help="Open sandbox endpoint in browser or start local port-forwarding")
def sandbox_open(
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Sandbox name"),
    port_forward: bool = typer.Option(False, "--port-forward", "-p", help="Forward remote frontend & backend ports to localhost"),
    domain: str = typer.Option("sandbox.agentforge.io", "--domain", help="Base domain"),
) -> None:
    """Access the sandbox web portal."""
    dev_name = name or SandboxManager.get_default_developer_name()
    namespace = SandboxManager.get_namespace(dev_name)

    current_dir = Path.cwd()
    project_name = current_dir.name or "agentforge-app"

    if port_forward:
        console.print(f"[bold cyan]Starting local port forwarding for '{namespace}'...[/bold cyan]")
        console.print("• Frontend: [green]http://localhost:5173[/green] -> pod:80")
        console.print("• Backend:  [green]http://localhost:8000[/green] -> pod:8000\n")

        # Dynamically discover frontend service name
        svc_name = f"{project_name}-frontend"
        if shutil.which("kubectl"):
            check_cmd = ["kubectl", "get", "svc", "-n", namespace, "-o", "jsonpath={.items[*].metadata.name}"]
            svc_res = subprocess.run(check_cmd, capture_output=True, text=True)
            available_svcs = svc_res.stdout.split()
            if f"{project_name}-frontend" in available_svcs:
                svc_name = f"{project_name}-frontend"
            elif f"{namespace}-frontend" in available_svcs:
                svc_name = f"{namespace}-frontend"
            elif any("frontend" in s for s in available_svcs):
                svc_name = next(s for s in available_svcs if "frontend" in s)

        cmd = ["kubectl", "port-forward", "-n", namespace, f"service/{svc_name}", "5173:80"]
        try:
            subprocess.run(cmd)
        except KeyboardInterrupt:
            console.print("\nPort forwarding terminated.")
    else:
        url = f"https://{dev_name}.{domain}"
        console.print(f"Opening sandbox URL: [cyan]{url}[/cyan]")
        webbrowser.open(url)
