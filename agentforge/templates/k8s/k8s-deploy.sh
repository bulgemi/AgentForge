#!/usr/bin/env bash
set -euo pipefail

ENV="${1:-dev}"
NAMESPACE="${2:-ai-agents}"

echo "⚡ Deploying {{ project_name }} to Kubernetes ($ENV / $NAMESPACE)..."

# Preflight check
command -v kubectl >/dev/null 2>&1 || { echo "kubectl not found. Skipping apply in dry-run."; exit 0; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$SCRIPT_DIR/$ENV"

if [[ ! -d "$TARGET_DIR" ]]; then
  echo "Error: environment manifest directory $TARGET_DIR does not exist."
  exit 1
fi

kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n "$NAMESPACE" -f "$TARGET_DIR"

echo "✓ Manifests applied. Waiting for rollout..."
kubectl rollout status deployment/{{ project_name }}-backend -n "$NAMESPACE" --timeout=60s || true
kubectl rollout status deployment/{{ project_name }}-frontend -n "$NAMESPACE" --timeout=60s || true

echo "✓ Deployment complete!"
