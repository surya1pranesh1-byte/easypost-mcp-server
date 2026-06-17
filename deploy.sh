#!/usr/bin/env bash
# =============================================================================
# EasyPost MCP Server — GCP Cloud Run Deployment Script
#
# Usage:
#   export GCP_PROJECT_ID=my-project
#   export EASYPOST_API_KEY=EZAK...
#   bash deploy.sh [--setup | --deploy | --secrets | --monitoring]
#
# Flags:
#   --setup       First-time GCP service setup (enable APIs, Artifact Registry,
#                 secrets). Run once per project.
#   --deploy      Build + push image + deploy to Cloud Run.
#   --secrets     (Re-)populate Secret Manager values.
#   --monitoring  Create log-based metrics and alerting policies.
#   (no flag)     Runs --setup + --deploy + --update-env in sequence.
# =============================================================================

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────
PROJECT_ID="${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-easypost-mcp}"
REPO_NAME="${REPO_NAME:-easypost-mcp}"
IMAGE_BASE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${SERVICE_NAME}"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD 2>/dev/null || echo latest)}"
IMAGE="${IMAGE_BASE}:${IMAGE_TAG}"

# ── Helpers ───────────────────────────────────────────────────────────────────
info()    { echo -e "\033[1;34m[INFO]\033[0m  $*"; }
success() { echo -e "\033[1;32m[OK]\033[0m    $*"; }
warn()    { echo -e "\033[1;33m[WARN]\033[0m  $*"; }
die()     { echo -e "\033[1;31m[ERROR]\033[0m $*" >&2; exit 1; }

require_env() {
  local var="$1"
  [[ -n "${!var:-}" ]] || die "$var must be set in environment"
}

# ── Step 1: Enable required GCP APIs ─────────────────────────────────────────
setup_services() {
  info "Enabling required GCP APIs..."
  gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com \
    cloudmonitoring.googleapis.com \
    logging.googleapis.com \
    --project="${PROJECT_ID}"
  success "GCP APIs enabled"
}

# ── Step 2: Create Artifact Registry repository ───────────────────────────────
setup_artifact_registry() {
  info "Checking Artifact Registry repository '${REPO_NAME}'..."
  if gcloud artifacts repositories describe "${REPO_NAME}" \
      --location="${REGION}" --project="${PROJECT_ID}" &>/dev/null; then
    warn "Repository '${REPO_NAME}' already exists — skipping creation"
  else
    gcloud artifacts repositories create "${REPO_NAME}" \
      --repository-format=docker \
      --location="${REGION}" \
      --description="EasyPost MCP Server container images" \
      --project="${PROJECT_ID}"
    success "Artifact Registry repository created: ${REPO_NAME}"
  fi

  # Configure Docker auth for Artifact Registry
  gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet
  success "Docker authenticated for Artifact Registry"
}

# ── Step 3: Create / update secrets in Secret Manager ────────────────────────
setup_secrets() {
  require_env EASYPOST_API_KEY

  info "Configuring Secret Manager..."

  create_or_update_secret() {
    local name="$1"
    local value="$2"
    if gcloud secrets describe "${name}" --project="${PROJECT_ID}" &>/dev/null; then
      warn "Secret '${name}' exists — adding new version"
      echo -n "${value}" | gcloud secrets versions add "${name}" \
        --data-file=- --project="${PROJECT_ID}"
    else
      echo -n "${value}" | gcloud secrets create "${name}" \
        --data-file=- --replication-policy=automatic --project="${PROJECT_ID}"
      success "Secret created: ${name}"
    fi
  }

  create_or_update_secret "easypost-api-key"      "${EASYPOST_API_KEY}"

  success "Secrets configured in Secret Manager"

  # Grant Cloud Run default service account access to these secrets
  local sa="${PROJECT_ID}@appspot.gserviceaccount.com"
  info "Granting Secret Manager access to service account: ${sa}"
  gcloud secrets add-iam-policy-binding "easypost-api-key" \
    --member="serviceAccount:${sa}" \
    --role="roles/secretmanager.secretAccessor" \
    --project="${PROJECT_ID}" \
    --quiet || warn "Could not bind IAM for easypost-api-key — ensure the service account is correct"
  success "IAM bindings applied"
}

# ── Step 4: Build + push Docker image ────────────────────────────────────────
build_and_push() {
  info "Building Docker image: ${IMAGE}"
  docker build \
    --tag "${IMAGE}" \
    --tag "${IMAGE_BASE}:latest" \
    --cache-from "${IMAGE_BASE}:latest" \
    --build-arg BUILDKIT_INLINE_CACHE=1 \
    .

  info "Pushing image to Artifact Registry..."
  docker push "${IMAGE}"
  docker push "${IMAGE_BASE}:latest"
  success "Image pushed: ${IMAGE}"
}

# ── Step 5: Deploy to Cloud Run ───────────────────────────────────────────────
deploy_cloud_run() {
  info "Deploying '${SERVICE_NAME}' to Cloud Run (region: ${REGION})..."

  gcloud run deploy "${SERVICE_NAME}" \
    --image="${IMAGE}" \
    --region="${REGION}" \
    --platform=managed \
    --port=8080 \
    --cpu=1 \
    --memory=512Mi \
    --concurrency=80 \
    --min-instances=1 \
    --max-instances=10 \
    --timeout=60s \
    --set-secrets="EASYPOST_API_KEY=easypost-api-key:latest" \
    --set-env-vars="NODE_ENV=production,LOG_LEVEL=info,EASYPOST_MODE=production,MCP_HTTP_HOST=0.0.0.0" \
    --allow-unauthenticated \
    --project="${PROJECT_ID}"

  success "Deployed to Cloud Run"

  # Print the service URL
  SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --format="value(status.url)")
  success "Service URL: ${SERVICE_URL}"
  echo "SERVICE_URL=${SERVICE_URL}" > .deploy-output
}

# ── Step 6: Create log-based metrics for monitoring ───────────────────────────
setup_monitoring() {
  info "Creating Cloud Monitoring log-based metrics..."

  # Helper: create metric if it doesn't exist
  create_log_metric() {
    local name="$1"
    local description="$2"
    local filter="$3"
    local label_key="$4"
    local label_field="$5"

    if gcloud logging metrics describe "${name}" --project="${PROJECT_ID}" &>/dev/null; then
      warn "Log metric '${name}' already exists — skipping"
      return
    fi

    # Write metric descriptor JSON to a temp file
    local tmpfile
    tmpfile=$(mktemp /tmp/metric-XXXXXX.json)
    cat >"${tmpfile}" <<JSON
{
  "name": "${name}",
  "description": "${description}",
  "filter": "${filter}",
  "metricDescriptor": {
    "metricKind": "DELTA",
    "valueType": "INT64",
    "labels": [
      {
        "key": "${label_key}",
        "valueType": "STRING",
        "description": "Tool name"
      }
    ]
  },
  "labelExtractors": {
    "${label_key}": "EXTRACT(jsonPayload.${label_field})"
  }
}
JSON

    gcloud logging metrics create "${name}" \
      --config-from-file="${tmpfile}" \
      --project="${PROJECT_ID}"
    rm -f "${tmpfile}"
    success "Created log metric: ${name}"
  }

  # Tool invocation count — use to track usage per tool
  create_log_metric \
    "easypost_mcp_tool_calls" \
    "Number of MCP tool invocations" \
    'resource.type="cloud_run_revision" jsonPayload.event="MCP tool called"' \
    "tool_name" \
    "tool_name"

  # Tool error count — use to track error rate per tool
  create_log_metric \
    "easypost_mcp_tool_errors" \
    "Number of MCP tool errors" \
    'resource.type="cloud_run_revision" jsonPayload.event="Tool execution failed"' \
    "tool_name" \
    "tool_name"

  # Tool latency — distribution metric for p50/p95/p99 via Log-based Metrics
  # Note: Cloud Run request latency is also available natively in Cloud Monitoring.
  if gcloud logging metrics describe "easypost_mcp_tool_latency" --project="${PROJECT_ID}" &>/dev/null; then
    warn "Log metric 'easypost_mcp_tool_latency' already exists — skipping"
  else
    local tmpfile
    tmpfile=$(mktemp /tmp/metric-XXXXXX.json)
    cat >"${tmpfile}" <<JSON
{
  "name": "easypost_mcp_tool_latency",
  "description": "MCP tool execution latency in milliseconds",
  "filter": "resource.type=\"cloud_run_revision\" jsonPayload.event=\"MCP tool completed\"",
  "metricDescriptor": {
    "metricKind": "DELTA",
    "valueType": "DISTRIBUTION",
    "unit": "ms",
    "labels": [
      {
        "key": "tool_name",
        "valueType": "STRING",
        "description": "Tool name"
      }
    ]
  },
  "valueExtractor": "EXTRACT(jsonPayload.latency_ms)",
  "labelExtractors": {
    "tool_name": "EXTRACT(jsonPayload.tool_name)"
  }
}
JSON
    gcloud logging metrics create "easypost_mcp_tool_latency" \
      --config-from-file="${tmpfile}" \
      --project="${PROJECT_ID}"
    rm -f "${tmpfile}"
    success "Created log metric: easypost_mcp_tool_latency"
  fi

  success "Cloud Monitoring log-based metrics created"
  info "View metrics at: https://console.cloud.google.com/monitoring/metrics-explorer?project=${PROJECT_ID}"
  info "Create dashboards / alerts from: logging/user/easypost_mcp_tool_calls, easypost_mcp_tool_errors, easypost_mcp_tool_latency"
}

# ── Entrypoint ────────────────────────────────────────────────────────────────
main() {
  local mode="${1:---all}"

  gcloud config set project "${PROJECT_ID}" --quiet

  case "${mode}" in
    --setup)
      setup_services
      setup_artifact_registry
      setup_secrets
      ;;
    --deploy)
      build_and_push
      deploy_cloud_run
      ;;
    --secrets)
      setup_secrets
      ;;
    --monitoring)
      setup_monitoring
      ;;
    --all | "")
      setup_services
      setup_artifact_registry
      setup_secrets
      build_and_push
      deploy_cloud_run
      setup_monitoring
      ;;
    *)
      die "Unknown flag: ${mode}. Use --setup | --deploy | --secrets | --monitoring"
      ;;
  esac

  echo ""
  success "Done."
}

main "$@"
