"""Real-time local file watcher and live sync engine for developer sandboxes."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable, Optional

from rich.console import Console

console = Console()


class FastFileSyncer:
    """Watches local source files and streams changes to remote sandbox pods."""

    def __init__(
        self,
        namespace: str,
        local_dir: Path,
        remote_dest: str = "/app/src",
        pod_component: str = "backend",
    ) -> None:
        self.namespace = namespace
        self.local_dir = local_dir.resolve()
        self.remote_dest = remote_dest
        self.pod_component = pod_component
        self._cached_pod: Optional[str] = None
        self._last_mtimes: dict[str, float] = {}

    def get_target_pod(self) -> Optional[str]:
        """Query kubectl for the running pod of the target component."""
        if not shutil.which("kubectl"):
            return None

        selectors = [
            f"app.kubernetes.io/component={self.pod_component}",
            f"app.kubernetes.io/name={self.pod_component}",
        ]
        for sel in selectors:
            cmd = [
                "kubectl",
                "get",
                "pods",
                "-n",
                self.namespace,
                "-l",
                sel,
                "--field-selector=status.phase=Running",
                "-o",
                "jsonpath={.items[0].metadata.name}",
            ]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if res.returncode == 0 and res.stdout.strip():
                    self._cached_pod = res.stdout.strip()
                    return self._cached_pod
            except Exception:
                pass

        # Fallback: find any running pod containing the component name
        try:
            cmd = [
                "kubectl",
                "get",
                "pods",
                "-n",
                self.namespace,
                "--field-selector=status.phase=Running",
                "-o",
                "jsonpath={.items[*].metadata.name}",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                for pod_name in res.stdout.split():
                    if self.pod_component in pod_name:
                        self._cached_pod = pod_name
                        return self._cached_pod
        except Exception:
            pass

        return None

    def scan_changes(self) -> list[Path]:
        """Scan directory and detect newly modified or created files."""
        changed: list[Path] = []
        if not self.local_dir.exists():
            return changed

        for root, dirs, files in os.walk(self.local_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
            for f in files:
                if f.startswith(".") or f.endswith(".pyc"):
                    continue
                file_path = Path(root) / f
                try:
                    mtime = file_path.stat().st_mtime
                    rel_key = str(file_path.relative_to(self.local_dir))
                    if rel_key not in self._last_mtimes:
                        self._last_mtimes[rel_key] = mtime
                    elif self._last_mtimes[rel_key] < mtime:
                        self._last_mtimes[rel_key] = mtime
                        changed.append(file_path)
                except OSError:
                    continue
        return changed

    def sync_file_to_pod(self, pod_name: str, file_path: Path) -> bool:
        """Copy a modified file into the container via kubectl cp."""
        rel_path = file_path.relative_to(self.local_dir)
        dest_base = self.remote_dest.rstrip("/")
        target_path = f"{dest_base}/{rel_path}"
        dest_in_pod = f"{self.namespace}/{pod_name}:{target_path}"

        cmd = ["kubectl", "cp", str(file_path), dest_in_pod, "-c", self.pod_component]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return res.returncode == 0
        except Exception:
            return False

    def start_watch_loop(self, interval_seconds: float = 1.0, on_sync: Optional[Callable[[Path], None]] = None) -> None:
        """Run blocking polling watch loop with graceful keyboard interrupt."""
        console.print(f"[bold cyan]⚡ Live Sync Active:[/bold cyan] {self.local_dir} -> [magenta]{self.namespace}[/magenta]:{self.remote_dest}")
        console.print("[dim]Press Ctrl+C to stop watching.[/dim]\n")

        # Initial baseline scan
        self.scan_changes()

        try:
            while True:
                time.sleep(interval_seconds)
                changed_files = self.scan_changes()
                if not changed_files:
                    continue

                pod_name = self.get_target_pod()
                if not pod_name:
                    console.print(f"[yellow]⚠ Waiting for running {self.pod_component} pod in {self.namespace}...[/yellow]")
                    continue

                for f in changed_files:
                    rel = f.relative_to(self.local_dir)
                    success = self.sync_file_to_pod(pod_name, f)
                    if success:
                        console.print(f"[bold green]✓ Live Synced:[/bold green] {rel} -> [cyan]{pod_name}[/cyan]")
                        if on_sync:
                            on_sync(f)
                    else:
                        console.print(f"[bold red]✗ Failed to sync:[/bold red] {rel}")
        except KeyboardInterrupt:
            console.print("\n[yellow]Watch loop stopped.[/yellow]")
