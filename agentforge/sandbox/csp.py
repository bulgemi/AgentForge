"""Unified Multi-CSP Kubernetes adapters for Developer Sandbox."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Mapping, Type


class BaseCSPAdapter(ABC):
    """Abstract base adapter defining CSP-specific Kubernetes behaviors."""

    @property
    @abstractmethod
    def csp_name(self) -> str:
        """Return the short name of the CSP (e.g. 'aws', 'gcp', 'azure')."""

    @property
    @abstractmethod
    def default_ingress_class(self) -> str:
        """Return the default ingress class name for this CSP."""

    @abstractmethod
    def get_workload_identity_annotations(self, role_or_sa_id: str) -> dict[str, str]:
        """Return ServiceAccount annotations for Workload Identity / IRSA."""

    @abstractmethod
    def get_ingress_annotations(
        self,
        host: str,
        tls_cert_id: str | None = None,
        custom_annotations: Mapping[str, str] | None = None,
    ) -> dict[str, str]:
        """Return Ingress annotations required for cloud-native load balancer routing."""

    @abstractmethod
    def get_storage_class(self) -> str:
        """Return default storage class for persistent volumes."""

    @abstractmethod
    def get_dns_helper_info(self, domain_suffix: str) -> str:
        """Return DNS instructions or status hints for wildcard subdomains."""


class AWSEKSAdapter(BaseCSPAdapter):
    """Adapter for AWS Elastic Kubernetes Service (EKS)."""

    @property
    def csp_name(self) -> str:
        return "aws"

    @property
    def default_ingress_class(self) -> str:
        return "alb"

    def get_workload_identity_annotations(self, role_or_sa_id: str) -> dict[str, str]:
        if not role_or_sa_id:
            return {}
        return {"eks.amazonaws.com/role-arn": role_or_sa_id}

    def get_ingress_annotations(
        self,
        host: str,
        tls_cert_id: str | None = None,
        custom_annotations: Mapping[str, str] | None = None,
    ) -> dict[str, str]:
        ann: dict[str, str] = {
            "kubernetes.io/ingress.class": "alb",
            "alb.ingress.kubernetes.io/scheme": "internet-facing",
            "alb.ingress.kubernetes.io/target-type": "ip",
            "alb.ingress.kubernetes.io/listen-ports": '[{"HTTP": 80}, {"HTTPS": 443}]',
        }
        if tls_cert_id:
            ann["alb.ingress.kubernetes.io/certificate-arn"] = tls_cert_id
            ann["alb.ingress.kubernetes.io/ssl-redirect"] = "443"
        if custom_annotations:
            ann.update(custom_annotations)
        return ann

    def get_storage_class(self) -> str:
        return "gp3"

    def get_dns_helper_info(self, domain_suffix: str) -> str:
        return f"Route53 Wildcard Alias: *.sandbox.{domain_suffix} -> AWS ALB DualStack DNS"


class GCPGKEAdapter(BaseCSPAdapter):
    """Adapter for Google Kubernetes Engine (GKE)."""

    @property
    def csp_name(self) -> str:
        return "gcp"

    @property
    def default_ingress_class(self) -> str:
        return "gce"

    def get_workload_identity_annotations(self, role_or_sa_id: str) -> dict[str, str]:
        if not role_or_sa_id:
            return {}
        return {"iam.gke.io/gcp-service-account": role_or_sa_id}

    def get_ingress_annotations(
        self,
        host: str,
        tls_cert_id: str | None = None,
        custom_annotations: Mapping[str, str] | None = None,
    ) -> dict[str, str]:
        ann: dict[str, str] = {
            "kubernetes.io/ingress.class": "gce",
        }
        if tls_cert_id:
            ann["networking.gke.io/managed-certificates"] = tls_cert_id
            ann["kubernetes.io/ingress.allow-http"] = "false"
        if custom_annotations:
            ann.update(custom_annotations)
        return ann

    def get_storage_class(self) -> str:
        return "standard-rwo"

    def get_dns_helper_info(self, domain_suffix: str) -> str:
        return f"Cloud DNS Wildcard A Record: *.sandbox.{domain_suffix} -> GKE Static Global IP"


class AzureAKSAdapter(BaseCSPAdapter):
    """Adapter for Azure Kubernetes Service (AKS)."""

    @property
    def csp_name(self) -> str:
        return "azure"

    @property
    def default_ingress_class(self) -> str:
        return "azure-application-gateway"

    def get_workload_identity_annotations(self, role_or_sa_id: str) -> dict[str, str]:
        if not role_or_sa_id:
            return {}
        return {"azure.workload.identity/client-id": role_or_sa_id}

    def get_ingress_annotations(
        self,
        host: str,
        tls_cert_id: str | None = None,
        custom_annotations: Mapping[str, str] | None = None,
    ) -> dict[str, str]:
        ann: dict[str, str] = {
            "kubernetes.io/ingress.class": "azure/application-gateway",
            "appgw.ingress.kubernetes.io/ssl-redirect": "true",
        }
        if tls_cert_id:
            ann["appgw.ingress.kubernetes.io/appgw-ssl-certificate"] = tls_cert_id
        if custom_annotations:
            ann.update(custom_annotations)
        return ann

    def get_storage_class(self) -> str:
        return "managed-csi"

    def get_dns_helper_info(self, domain_suffix: str) -> str:
        return f"Azure DNS Wildcard CNAME/A: *.sandbox.{domain_suffix} -> AppGateway Public IP"


CSP_REGISTRY: Dict[str, Type[BaseCSPAdapter]] = {
    "aws": AWSEKSAdapter,
    "eks": AWSEKSAdapter,
    "gcp": GCPGKEAdapter,
    "gke": GCPGKEAdapter,
    "azure": AzureAKSAdapter,
    "aks": AzureAKSAdapter,
}


def get_csp_adapter(csp_name: str) -> BaseCSPAdapter:
    """Retrieve the appropriate CSP adapter instance by name."""
    clean = csp_name.strip().lower()
    adapter_cls = CSP_REGISTRY.get(clean)
    if not adapter_cls:
        valid = ", ".join(sorted(set(["aws", "gcp", "azure"])))
        raise ValueError(f"Unsupported CSP '{csp_name}'. Supported CSPs are: {valid}")
    return adapter_cls()
