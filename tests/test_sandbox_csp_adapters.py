"""Tests for Multi-CSP Kubernetes adapters."""

from __future__ import annotations

import pytest

from agentforge.sandbox.csp import (
    AWSEKSAdapter,
    AzureAKSAdapter,
    GCPGKEAdapter,
    get_csp_adapter,
)


def test_aws_adapter():
    adapter = get_csp_adapter("aws")
    assert isinstance(adapter, AWSEKSAdapter)
    assert adapter.csp_name == "aws"

    # IRSA
    irsa = adapter.get_workload_identity_annotations("arn:aws:iam::123456789012:role/MyRole")
    assert irsa == {"eks.amazonaws.com/role-arn": "arn:aws:iam::123456789012:role/MyRole"}
    assert adapter.get_workload_identity_annotations("") == {}

    # Ingress
    ingress_ann = adapter.get_ingress_annotations(
        host="alice.sandbox.example.com",
        tls_cert_id="arn:aws:acm:us-east-1:123:certificate/abc",
    )
    assert ingress_ann["kubernetes.io/ingress.class"] == "alb"
    assert ingress_ann["alb.ingress.kubernetes.io/scheme"] == "internet-facing"
    assert ingress_ann["alb.ingress.kubernetes.io/certificate-arn"] == "arn:aws:acm:us-east-1:123:certificate/abc"
    assert adapter.get_storage_class() == "gp3"


def test_gcp_adapter():
    adapter = get_csp_adapter("gcp")
    assert isinstance(adapter, GCPGKEAdapter)
    assert adapter.csp_name == "gcp"

    # Workload Identity
    wi = adapter.get_workload_identity_annotations("my-sa@my-proj.iam.gserviceaccount.com")
    assert wi == {"iam.gke.io/gcp-service-account": "my-sa@my-proj.iam.gserviceaccount.com"}

    # Ingress
    ingress_ann = adapter.get_ingress_annotations(
        host="alice.sandbox.example.com",
        tls_cert_id="my-gke-cert",
    )
    assert ingress_ann["kubernetes.io/ingress.class"] == "gce"
    assert ingress_ann["networking.gke.io/managed-certificates"] == "my-gke-cert"
    assert adapter.get_storage_class() == "standard-rwo"


def test_azure_adapter():
    adapter = get_csp_adapter("azure")
    assert isinstance(adapter, AzureAKSAdapter)
    assert adapter.csp_name == "azure"

    # Workload Identity
    wi = adapter.get_workload_identity_annotations("00000000-0000-0000-0000-000000000000")
    assert wi == {"azure.workload.identity/client-id": "00000000-0000-0000-0000-000000000000"}

    # Ingress
    ingress_ann = adapter.get_ingress_annotations(
        host="alice.sandbox.example.com",
        tls_cert_id="my-appgw-cert",
    )
    assert ingress_ann["kubernetes.io/ingress.class"] == "azure/application-gateway"
    assert ingress_ann["appgw.ingress.kubernetes.io/appgw-ssl-certificate"] == "my-appgw-cert"
    assert adapter.get_storage_class() == "managed-csi"


def test_invalid_csp():
    with pytest.raises(ValueError, match="Unsupported CSP 'ibm'"):
        get_csp_adapter("ibm")
