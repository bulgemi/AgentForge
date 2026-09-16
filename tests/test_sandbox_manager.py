"""Tests for SandboxManager and lifecycle governance."""

from __future__ import annotations

import datetime

import pytest
import yaml

from agentforge.sandbox.manager import SandboxManager, parse_ttl


def test_parse_ttl():
    assert parse_ttl("30m") == datetime.timedelta(minutes=30)
    assert parse_ttl("4h") == datetime.timedelta(hours=4)
    assert parse_ttl("24h") == datetime.timedelta(hours=24)
    assert parse_ttl("2d") == datetime.timedelta(days=2)

    with pytest.raises(ValueError, match="Invalid TTL format"):
        parse_ttl("invalid")


def test_get_namespace():
    assert SandboxManager.get_namespace("Alice") == "sandbox-alice"
    assert SandboxManager.get_namespace("john.doe_test") == "sandbox-john-doe-test"
    assert SandboxManager.get_namespace("dev-123") == "sandbox-dev-123"


def test_generate_sandbox_artifacts_aws():
    manager = SandboxManager()
    manifests = manager.generate_sandbox_artifacts(
        developer_name="charlie",
        project_name="agentforge-test",
        csp_name="aws",
        ttl="4h",
        domain_suffix="mytest.io",
        shared_db=False,
        rancher_project_id="c-123:p-456",
    )

    assert "namespace.yaml" in manifests
    assert "networkpolicy.yaml" in manifests
    assert "resourcequota.yaml" in manifests
    assert "values-sandbox.yaml" in manifests

    # Check namespace manifest
    ns_data = yaml.safe_load(manifests["namespace.yaml"])
    assert ns_data["metadata"]["name"] == "sandbox-charlie"
    assert ns_data["metadata"]["labels"]["agentforge.io/developer"] == "charlie"
    assert ns_data["metadata"]["annotations"]["agentforge.io/ttl"] == "4h"
    assert ns_data["metadata"]["annotations"]["field.cattle.io/projectId"] == "c-123:p-456"

    # Check networkpolicy manifest
    netpol_data = yaml.safe_load(manifests["networkpolicy.yaml"])
    assert netpol_data["metadata"]["namespace"] == "sandbox-charlie"
    assert netpol_data["kind"] == "NetworkPolicy"

    # Check resourcequota and limitrange manifest
    docs = list(yaml.safe_load_all(manifests["resourcequota.yaml"]))
    quota_data = docs[0]
    limit_data = docs[1]

    assert quota_data["metadata"]["namespace"] == "sandbox-charlie"
    assert quota_data["spec"]["hard"]["limits.cpu"] == "2000m"
    assert quota_data["spec"]["hard"]["limits.memory"] == "2Gi"
    assert quota_data["spec"]["hard"]["requests.cpu"] == "500m"
    assert quota_data["spec"]["hard"]["requests.memory"] == "1Gi"

    assert limit_data["metadata"]["namespace"] == "sandbox-charlie"
    assert limit_data["spec"]["limits"][0]["default"]["cpu"] == "500m"
    assert limit_data["spec"]["limits"][0]["default"]["memory"] == "512Mi"
    assert limit_data["spec"]["limits"][0]["defaultRequest"]["cpu"] == "100m"
    assert limit_data["spec"]["limits"][0]["defaultRequest"]["memory"] == "128Mi"

    # Check values override
    values_data = yaml.safe_load(manifests["values-sandbox.yaml"])
    assert values_data["backend"]["replicaCount"] == 1
    assert values_data["ingress"]["className"] == "alb"
    assert values_data["ingress"]["hosts"][0]["host"] == "charlie.sandbox.mytest.io"
    assert values_data["stateful"]["postgres"]["embedded"] is True


def test_generate_sandbox_artifacts_gcp():
    manager = SandboxManager()
    manifests = manager.generate_sandbox_artifacts(
        developer_name="dave",
        project_name="gcp-agent",
        csp_name="gcp",
        ttl="12h",
        domain_suffix="cloud.io",
        shared_db=True,
    )

    values_data = yaml.safe_load(manifests["values-sandbox.yaml"])
    assert values_data["ingress"]["className"] == "gce"
    assert values_data["ingress"]["hosts"][0]["host"] == "dave.sandbox.cloud.io"
    assert values_data["stateful"]["postgres"]["embedded"] is False


def test_generate_sandbox_artifacts_azure():
    manager = SandboxManager()
    manifests = manager.generate_sandbox_artifacts(
        developer_name="eve",
        project_name="azure-agent",
        csp_name="azure",
        ttl="1d",
        domain_suffix="azure.io",
    )

    values_data = yaml.safe_load(manifests["values-sandbox.yaml"])
    assert values_data["ingress"]["className"] == "azure-application-gateway"
    assert values_data["ingress"]["hosts"][0]["host"] == "eve.sandbox.azure.io"
