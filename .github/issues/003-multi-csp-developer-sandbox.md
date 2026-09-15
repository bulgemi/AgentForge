---
title: "feat(sandbox): multi-CSP (AWS EKS, GCP GKE, Azure AKS) developer sandbox with Rancher"
labels: ["feature", "stage:done", "status:completed", "rancher", "eks", "gke", "aks", "sandbox", "cli"]
status: "completed"
created_at: "2026-09-15T20:10:00+09:00"
closed_at: "2026-09-15T20:19:45+09:00"
---

# feat(sandbox): Multi-CSP (AWS EKS, GCP GKE, Azure AKS) Developer Sandbox with Rancher

## Overview
Implement an on-demand developer sandbox CLI and management framework (`af sandbox`) supporting multi-cloud Kubernetes clusters (AWS EKS, GCP GKE, Azure AKS) orchestrated via Rancher.

## Key Capabilities
1. **Multi-CSP Abstraction**:
   - `BaseCSPAdapter`, `AWSEKSAdapter`, `GCPGKEAdapter`, `AzureAKSAdapter` for Workload Identity, Ingress, and Storage.
2. **Lifecycle & Isolation**:
   - Dynamic `sandbox-<user>` namespace with NetworkPolicy, ResourceQuota, and TTL annotations.
3. **Live Sync (Dev Loop)**:
   - `af sandbox watch`: Real-time file sync to remote sandbox pods for zero-rebuild hot reload.
4. **Endpoint & Cost Governance**:
   - `af sandbox open` (hybrid wildcard ingress & port-forwarding).
   - `af sandbox pause` / `af sandbox resume` (scale to 0).
   - Auto-cleanup of expired sandboxes.

## Tasks
- [x] Create `agentforge/sandbox/csp/base.py`
- [x] Create `agentforge/sandbox/csp/aws.py`
- [x] Create `agentforge/sandbox/csp/gcp.py`
- [x] Create `agentforge/sandbox/csp/azure.py`
- [x] Create `agentforge/sandbox/csp/__init__.py`
- [x] Create `agentforge/templates/sandbox/networkpolicy.yaml`
- [x] Create `agentforge/templates/sandbox/resourcequota.yaml`
- [x] Create `agentforge/templates/sandbox/values-sandbox.yaml`
- [x] Create `agentforge/sandbox/manager.py`
- [x] Create `agentforge/sandbox/watcher.py`
- [x] Create `agentforge/sandbox/__init__.py`
- [x] Create `agentforge/cli/commands/sandbox.py`
- [x] Register `sandbox` in `agentforge/cli/main.py`
- [x] Update `docs/infrastructure.md`
- [x] Write unit & CLI tests in `tests/test_sandbox_*.py`
- [x] Verify test suite passes (204/204 tests passing)
- [x] Document and verify local testing guide (Docker + Minikube + Rancher)
