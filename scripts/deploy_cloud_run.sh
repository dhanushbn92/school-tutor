#!/usr/bin/env bash
# Build the backend container and deploy it to Cloud Run.
#
# Required env vars (set before invoking, e.g. in scripts/deploy.env):
#   GCP_PROJECT       e.g. school-tuter-prod
#   GCP_REGION        e.g. asia-south1
#   AR_REPO           Artifact Registry repo name, e.g. school-tuter
#   SERVICE_NAME      Cloud Run service name, e.g. school-tuter-api
#   GCS_BUCKET        Bucket holding artifacts, e.g. school-tuter-artifacts
#   DATABASE_URL      Postgres URL (Supabase or Cloud SQL)
#   ALLOWED_ORIGINS   Comma-separated origins, e.g. https://school-tuter.web.app
#   JWT_SECRET        Long random string
#
# Optional env vars:
#   GROQ_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY  (LLM providers)
#   LLM_PROVIDER      "groq" | "openai" | "anthropic" | "stub"
#   IMAGE_TAG         Override the image tag (default: git short SHA or `latest`)
#
# This script is idempotent — run it on every deploy. The first run requires
# `gcloud auth login`, project + region defaults set, and the Artifact Registry
# repo + GCS bucket already created (see docs/deploy.md).

set -euo pipefail

# Load .env-style overrides if present.
if [[ -f "scripts/deploy.env" ]]; then
    # shellcheck disable=SC1091
    set -a; source scripts/deploy.env; set +a
fi

: "${GCP_PROJECT:?GCP_PROJECT is required}"
: "${GCP_REGION:?GCP_REGION is required}"
: "${AR_REPO:?AR_REPO is required}"
: "${SERVICE_NAME:?SERVICE_NAME is required}"
: "${GCS_BUCKET:?GCS_BUCKET is required}"
: "${DATABASE_URL:?DATABASE_URL is required}"
: "${ALLOWED_ORIGINS:?ALLOWED_ORIGINS is required}"
: "${JWT_SECRET:?JWT_SECRET is required}"

# On Windows + Git Bash, the bundled gcloud needs CLOUDSDK_PYTHON pointing at
# its own Python because the Microsoft Store `python` shim isn't on the bash
# PATH. Auto-discover it; harmless on Linux/macOS.
if [[ -z "${CLOUDSDK_PYTHON:-}" ]]; then
    candidate="C:/Users/${USER:-$USERNAME}/AppData/Local/Google/Cloud SDK/google-cloud-sdk/platform/bundledpython/python.exe"
    if [[ -f "$candidate" ]]; then
        export CLOUDSDK_PYTHON="$candidate"
    fi
fi

IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD 2>/dev/null || echo latest)}"
IMAGE="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/${AR_REPO}/${SERVICE_NAME}:${IMAGE_TAG}"

echo "==> Building image ${IMAGE}"
gcloud builds submit \
    --project "${GCP_PROJECT}" \
    --tag "${IMAGE}" \
    .

# Write env vars as YAML so values containing `,`, `@`, `#`, etc. (e.g. the
# Supabase DATABASE_URL with an `@` in the password) survive verbatim.
# `--set-env-vars` does naive splitting on a delimiter and breaks on these.
ENV_FILE="$(mktemp -t cloud_run_env.XXXXXX.yaml)"
trap 'rm -f "$ENV_FILE"' EXIT

# YAML scalars in double quotes need the literal " and \ escaped. We pipe
# through a tiny Python so we don't have to reason about edge cases.
emit_env() {
    "${CLOUDSDK_PYTHON:-python}" - <<PY > "$ENV_FILE"
import json, os
pairs = {
    "ARTIFACT_BACKEND": "gcs",
    "GCS_BUCKET": os.environ["GCS_BUCKET"],
    "DATABASE_URL": os.environ["DATABASE_URL"],
    "ALLOWED_ORIGINS": os.environ["ALLOWED_ORIGINS"],
    "JWT_SECRET": os.environ["JWT_SECRET"],
    "AUTO_CREATE_TABLES": "false",
    "ENVIRONMENT": "production",
}
for k in ("LLM_PROVIDER", "GROQ_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
    v = os.environ.get(k, "").strip()
    if v:
        pairs[k] = v
for k, v in pairs.items():
    # JSON-encoded string is a valid YAML double-quoted scalar.
    print(f"{k}: {json.dumps(v)}")
PY
}
emit_env

echo "==> Deploying ${SERVICE_NAME} to Cloud Run"
gcloud run deploy "${SERVICE_NAME}" \
    --project "${GCP_PROJECT}" \
    --region "${GCP_REGION}" \
    --image "${IMAGE}" \
    --platform managed \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 4 \
    --concurrency 40 \
    --timeout 120s \
    --env-vars-file "${ENV_FILE}"

URL="$(gcloud run services describe "${SERVICE_NAME}" \
    --project "${GCP_PROJECT}" \
    --region "${GCP_REGION}" \
    --format='value(status.url)')"
echo
echo "==> Deployed: ${URL}"
echo "    Set this in frontend/.env.production as VITE_API_BASE_URL,"
echo "    and add to ALLOWED_ORIGINS on the next deploy if it changed."
