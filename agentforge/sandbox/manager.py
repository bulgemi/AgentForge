"""Sandbox lifecycle and isolation manager for Multi-CSP Kubernetes clusters."""

from __future__ import annotations

import datetime
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Mapping, Optional

import yaml
from rich.console import Console

from .csp import get_csp_adapter, BaseCSPAdapter

console = Console()

PACKAGE_SANDBOX_TEMPLATES = Path(__file__).resolve().parent.parent / "templates" / "sandbox"


def parse_ttl(ttl_str: str) -> datetime.timedelta:
    """Parse human readable TTL string (e.g. 30m, 4h, 24h, 2d) into a timedelta."""
    pattern = re.match(r"^(\d+)\s*([mhd])$", ttl_str.strip().lower())
    if not pattern:
        raise ValueError(f"Invalid TTL format '{ttl_str}'. Expected format like '30m', '4h', '24h', or '2d'.")

    val = int(pattern.group(1))
    unit = pattern.group(2)
    if unit == "m":
        return datetime.timedelta(minutes=val)
    elif unit == "h":
        return datetime.timedelta(hours=val)
    elif unit == "d":
        return datetime.timedelta(days=val)
    return datetime.timedelta(hours=8)


def sanitize_k8s_name(name: str) -> str:
    """Ensure name complies with RFC 1123 DNS subdomain rules (lowercase, dashes only)."""
    return re.sub(r"[^a-z0-9-]", "-", name.lower()).strip("-")


def _sanitize_doc(obj: Any) -> Any:
    """Recursively sanitize Kubernetes resource names and references to conform to RFC 1123."""
    if isinstance(obj, dict):
        new_dict: dict[str, Any] = {}
        for k, v in obj.items():
            if k in ("name", "claimName") and isinstance(v, str):
                new_dict[k] = sanitize_k8s_name(v)
            elif k in ("app", "component") and isinstance(v, str):
                new_dict[k] = sanitize_k8s_name(v)
            elif isinstance(v, (dict, list)):
                new_dict[k] = _sanitize_doc(v)
            else:
                new_dict[k] = v
        return new_dict
    elif isinstance(obj, list):
        return [_sanitize_doc(item) for item in obj]
    return obj


class SandboxManager:
    """Orchestrates creation, governance, status checking, and teardown of sandboxes."""

    def __init__(self, templates_dir: Optional[Path] = None) -> None:
        self.templates_dir = templates_dir or PACKAGE_SANDBOX_TEMPLATES

    @staticmethod
    def get_default_developer_name() -> str:
        """Resolve clean developer username from environment or OS."""
        user = os.getenv("USER") or os.getenv("USERNAME") or "dev"
        # Sanitize for DNS-1123 label (lowercase alphanumeric and dash)
        clean = re.sub(r"[^a-z0-9-]", "-", user.lower()).strip("-")
        return clean or "dev"

    @classmethod
    def get_namespace(cls, developer_name: str) -> str:
        """Get the standardized namespace name for a developer."""
        clean = re.sub(r"[^a-z0-9-]", "-", developer_name.lower()).strip("-")
        if clean.startswith("sandbox-"):
            clean = clean[len("sandbox-") :]
        return f"sandbox-{clean or 'dev'}"

    def render_manifest(self, template_file: Path, context: Mapping[str, Any]) -> str:
        """Render simple token replacements into template file."""
        content = template_file.read_text(encoding="utf-8")
        for k, v in context.items():
            pattern = re.compile(r"\{\{\s*" + re.escape(k) + r"\s*\}\}")
            content = pattern.sub(str(v), content)
        return content

    def build_namespace_manifest(
        self,
        namespace: str,
        developer_name: str,
        ttl_str: str = "8h",
        rancher_project_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Construct Kubernetes Namespace manifest with TTL and Rancher Project annotations."""
        now = datetime.datetime.now(datetime.timezone.utc)
        delta = parse_ttl(ttl_str)
        expiry_iso = (now + delta).isoformat()

        annotations: dict[str, str] = {
            "agentforge.io/created-at": now.isoformat(),
            "agentforge.io/expires-at": expiry_iso,
            "agentforge.io/ttl": ttl_str,
        }
        if rancher_project_id:
            annotations["field.cattle.io/projectId"] = rancher_project_id

        return {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {
                "name": namespace,
                "labels": {
                    "agentforge.io/managed-by": "sandbox",
                    "agentforge.io/developer": developer_name,
                    "pod-security.kubernetes.io/enforce": "baseline",
                },
                "annotations": annotations,
            },
        }

    def generate_sandbox_artifacts(
        self,
        developer_name: str,
        project_name: str,
        csp_name: str = "aws",
        ttl: str = "8h",
        domain_suffix: str = "example.com",
        shared_db: bool = False,
        rancher_project_id: Optional[str] = None,
    ) -> dict[str, str]:
        """Generate all required YAML manifests for the sandbox."""
        adapter: BaseCSPAdapter = get_csp_adapter(csp_name)
        namespace = self.get_namespace(developer_name)

        context = {
            "sandbox_namespace": namespace,
            "developer_name": developer_name,
            "project_name": project_name,
            "ingress_class": adapter.default_ingress_class,
            "domain_suffix": domain_suffix,
            "embedded_postgres": "false" if shared_db else "true",
            "embedded_redis": "false" if shared_db else "true",
        }

        # 1. Namespace
        ns_dict = self.build_namespace_manifest(namespace, developer_name, ttl, rancher_project_id)
        ns_yaml = yaml.safe_dump(ns_dict, default_flow_style=False, sort_keys=False)

        # 2. NetworkPolicy
        netpol_tpl = self.templates_dir / "networkpolicy.yaml"
        netpol_yaml = self.render_manifest(netpol_tpl, context)

        # 3. ResourceQuota & LimitRange
        quota_tpl = self.templates_dir / "resourcequota.yaml"
        quota_yaml = self.render_manifest(quota_tpl, context)

        # 4. Values Sandbox Override
        values_tpl = self.templates_dir / "values-sandbox.yaml"
        values_yaml = self.render_manifest(values_tpl, context)

        return {
            "namespace.yaml": ns_yaml,
            "networkpolicy.yaml": netpol_yaml,
            "resourcequota.yaml": quota_yaml,
            "values-sandbox.yaml": values_yaml,
        }

    def apply_manifests(self, manifests: dict[str, str], dry_run: bool = False) -> None:
        """Apply Kubernetes manifests via kubectl apply."""
        if dry_run or not shutil.which("kubectl"):
            for name, content in manifests.items():
                console.print(f"\n[bold yellow]--- Manifest: {name} (Dry Run) ---[/bold yellow]")
                console.print(content.strip())
            return

        for name in ["namespace.yaml", "resourcequota.yaml", "networkpolicy.yaml"]:
            content = manifests.get(name)
            if not content:
                continue
            res = subprocess.run(["kubectl", "apply", "-f", "-"], input=content, text=True, capture_output=True)
            if res.returncode != 0:
                console.print(f"[bold red]Failed to apply {name}:[/bold red] {res.stderr}")
                raise RuntimeError(res.stderr)
            console.print(f"[green]✓ Applied {name}[/green]")

    def scale_deployments(self, namespace: str, replicas: int) -> bool:
        """Scale backend and frontend deployments in the sandbox namespace."""
        if not shutil.which("kubectl"):
            return False

        for comp in ["backend", "frontend"]:
            cmd = ["kubectl", "scale", "deployment", "-n", namespace, f"--replicas={replicas}", "-l", f"app.kubernetes.io/component={comp}"]
            subprocess.run(cmd, capture_output=True, text=True)
        return True

    def delete_namespace(self, namespace: str) -> bool:
        """Delete sandbox namespace and all contained resources."""
        if not shutil.which("kubectl"):
            return False

        cmd = ["kubectl", "delete", "namespace", namespace, "--wait=false"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.returncode == 0

    def deploy_k8s_workloads(
        self,
        namespace: str,
        k8s_dir: Path,
        domain_suffix: str = "sandbox.agentforge.io",
        dry_run: bool = False,
    ) -> list[str]:
        """Deploy Kubernetes manifests from k8s directory into target sandbox namespace."""
        manifest_files = sorted(list(k8s_dir.glob("*.yaml")) + list(k8s_dir.glob("*.yml")))
        applied_manifests: list[str] = []
        backend_svc_name: Optional[str] = None
        frontend_svc_name: Optional[str] = None

        for f in manifest_files:
            content = f.read_text(encoding="utf-8")
            docs = list(yaml.safe_load_all(content))
            updated_docs = []
            for raw_doc in docs:
                if not raw_doc:
                    continue
                # Sanitize all names and references (replace underscores with dashes for RFC 1123)
                doc = _sanitize_doc(raw_doc)
                # Ensure metadata.namespace is explicitly the sandbox namespace
                metadata = doc.setdefault("metadata", {})
                metadata["namespace"] = namespace
                # Ensure component label is present if missing
                labels = metadata.setdefault("labels", {})
                name = metadata.get("name", "")
                kind = doc.get("kind", "")
                if "backend" in name:
                    if "app.kubernetes.io/component" not in labels:
                        labels["app.kubernetes.io/component"] = "backend"
                    if kind == "Service":
                        backend_svc_name = name
                elif "frontend" in name:
                    if "app.kubernetes.io/component" not in labels:
                        labels["app.kubernetes.io/component"] = "frontend"
                    if kind == "Service":
                        frontend_svc_name = name
                updated_docs.append(doc)

            if not updated_docs:
                continue

            rendered = yaml.safe_dump_all(updated_docs, default_flow_style=False, sort_keys=False)
            applied_manifests.append(rendered)

            if dry_run or not shutil.which("kubectl"):
                console.print(f"\n[bold yellow]--- Workload: {f.name} (Target NS: {namespace}) ---[/bold yellow]")
                console.print(rendered.strip())
            else:
                res = subprocess.run(["kubectl", "apply", "-n", namespace, "-f", "-"], input=rendered, text=True, capture_output=True)
                if res.returncode != 0:
                    console.print(f"[bold red]Failed to apply workload {f.name}:[/bold red] {res.stderr}")
                    raise RuntimeError(res.stderr)
                console.print(f"[green]✓ Applied workload {f.name} to namespace '{namespace}'[/green]")

        # Automatically create Ingress if backend/frontend services exist and no ingress defined
        has_ingress = any("kind: Ingress" in m for m in applied_manifests)
        if not has_ingress and (backend_svc_name or frontend_svc_name):
            ingress_paths = []
            if backend_svc_name:
                ingress_paths.append({
                    "path": "/api",
                    "pathType": "Prefix",
                    "backend": {"service": {"name": backend_svc_name, "port": {"number": 8000}}},
                })
            if frontend_svc_name:
                ingress_paths.append({
                    "path": "/",
                    "pathType": "Prefix",
                    "backend": {"service": {"name": frontend_svc_name, "port": {"number": 80}}},
                })

            dev_clean = namespace.removeprefix("sandbox-")
            host = domain_suffix if domain_suffix.startswith(dev_clean) or domain_suffix.startswith(namespace) else f"{dev_clean}.{domain_suffix}"
            ingress_doc = {
                "apiVersion": "networking.k8s.io/v1",
                "kind": "Ingress",
                "metadata": {
                    "name": f"{namespace}-ingress",
                    "namespace": namespace,
                    "annotations": {
                        "nginx.ingress.kubernetes.io/ssl-redirect": "false",
                    },
                },
                "spec": {
                    "rules": [
                        {
                            "host": host,
                            "http": {"paths": ingress_paths},
                        }
                    ]
                },
            }
            rendered_ingress = yaml.safe_dump(ingress_doc, default_flow_style=False, sort_keys=False)
            applied_manifests.append(rendered_ingress)

            if dry_run or not shutil.which("kubectl"):
                console.print(f"\n[bold yellow]--- Ingress: {namespace}-ingress (Target NS: {namespace}) ---[/bold yellow]")
                console.print(rendered_ingress.strip())
            else:
                res = subprocess.run(["kubectl", "apply", "-n", namespace, "-f", "-"], input=rendered_ingress, text=True, capture_output=True)
                if res.returncode == 0:
                    console.print(f"[green]✓ Applied sandbox ingress to namespace '{namespace}'[/green]")

        return applied_manifests

