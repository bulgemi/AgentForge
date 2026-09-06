#!/bin/sh
set -eu

OPENSEARCH_URL="${OPENSEARCH_URL:-http://opensearch:9200}"
INDEX_TEMPLATE_NAME="${INDEX_TEMPLATE_NAME:-{{ project_name_snake }}-template}"
INDEX_TEMPLATE_FILE="${INDEX_TEMPLATE_FILE:-/config/agent-index-template.json}"

echo "[OpenSearch Init] Waiting for OpenSearch at ${OPENSEARCH_URL}..."
HEALTH_MAX_RETRIES=30
HEALTH_RETRY=0
until curl --fail --silent "${OPENSEARCH_URL}/_cluster/health?wait_for_status=yellow&timeout=5s" >/dev/null; do
  HEALTH_RETRY=$((HEALTH_RETRY + 1))
  if [ "${HEALTH_RETRY}" -ge "${HEALTH_MAX_RETRIES}" ]; then
    echo "[OpenSearch Init] Error: Timed out waiting for OpenSearch cluster health at ${OPENSEARCH_URL}." >&2
    exit 1
  fi
  echo "[OpenSearch Init] Cluster not ready yet. Retrying in 2s..."
  sleep 2
done

echo "[OpenSearch Init] Cluster is healthy."

if [ ! -f "${INDEX_TEMPLATE_FILE}" ]; then
  echo "[OpenSearch Init] Error: Template file ${INDEX_TEMPLATE_FILE} not found." >&2
  exit 1
fi

echo "[OpenSearch Init] Registering index template: ${INDEX_TEMPLATE_NAME}"
MAX_RETRIES=10
RETRY_COUNT=0
until curl --fail-with-body -sS -X PUT "${OPENSEARCH_URL}/_index_template/${INDEX_TEMPLATE_NAME}" \
  -H "Content-Type: application/json" \
  --data-binary "@${INDEX_TEMPLATE_FILE}"; do
  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [ "${RETRY_COUNT}" -ge "${MAX_RETRIES}" ]; then
    echo "[OpenSearch Init] Failed to register template after ${MAX_RETRIES} attempts." >&2
    exit 1
  fi
  echo "[OpenSearch Init] Registration attempt ${RETRY_COUNT} failed. Retrying in 2s..."
  sleep 2
done
echo ""
echo "[OpenSearch Init] Template ${INDEX_TEMPLATE_NAME} registered successfully."
echo "[OpenSearch Init] Completed."
