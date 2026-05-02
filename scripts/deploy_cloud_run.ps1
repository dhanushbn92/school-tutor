# Build the backend container and deploy it to Cloud Run.
#
# Required env vars (set before invoking, or in scripts/deploy.env.ps1):
#   GCP_PROJECT, GCP_REGION, AR_REPO, SERVICE_NAME, GCS_BUCKET,
#   DATABASE_URL, ALLOWED_ORIGINS, JWT_SECRET
#
# Optional: GROQ_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, LLM_PROVIDER, IMAGE_TAG.
#
# First-time setup (project + region defaults, Artifact Registry repo, GCS bucket)
# is documented in docs/deploy.md. This script is the per-deploy command.

$ErrorActionPreference = "Stop"

# Optional override file: dot-source if present.
if (Test-Path "scripts/deploy.env.ps1") {
    . "scripts/deploy.env.ps1"
}

function Require-EnvVar($name) {
    $val = (Get-Item "Env:$name" -ErrorAction SilentlyContinue).Value
    if (-not $val) { throw "$name is required" }
    return $val
}

$GCP_PROJECT     = Require-EnvVar "GCP_PROJECT"
$GCP_REGION      = Require-EnvVar "GCP_REGION"
$AR_REPO         = Require-EnvVar "AR_REPO"
$SERVICE_NAME    = Require-EnvVar "SERVICE_NAME"
$GCS_BUCKET      = Require-EnvVar "GCS_BUCKET"
$DATABASE_URL    = Require-EnvVar "DATABASE_URL"
$ALLOWED_ORIGINS = Require-EnvVar "ALLOWED_ORIGINS"
$JWT_SECRET      = Require-EnvVar "JWT_SECRET"

if (-not $env:IMAGE_TAG) {
    try { $env:IMAGE_TAG = (git rev-parse --short HEAD 2>$null) } catch {}
    if (-not $env:IMAGE_TAG) { $env:IMAGE_TAG = "latest" }
}
$IMAGE = "$GCP_REGION-docker.pkg.dev/$GCP_PROJECT/$AR_REPO/${SERVICE_NAME}:$env:IMAGE_TAG"

Write-Host "==> Building image $IMAGE"
gcloud builds submit --project $GCP_PROJECT --tag $IMAGE .
if ($LASTEXITCODE -ne 0) { throw "gcloud builds submit failed" }

# Write env vars as YAML so values containing `,`, `@`, `#`, etc. (e.g. the
# Supabase DATABASE_URL with an `@` in the password) survive verbatim.
# `--set-env-vars` does naive splitting on a delimiter and breaks on these.
$pairs = [ordered]@{
    ARTIFACT_BACKEND   = "gcs"
    GCS_BUCKET         = $GCS_BUCKET
    DATABASE_URL       = $DATABASE_URL
    ALLOWED_ORIGINS    = $ALLOWED_ORIGINS
    JWT_SECRET         = $JWT_SECRET
    AUTO_CREATE_TABLES = "false"
    ENVIRONMENT        = "production"
}
if ($env:LLM_PROVIDER)      { $pairs["LLM_PROVIDER"]      = $env:LLM_PROVIDER }
if ($env:GROQ_API_KEY)      { $pairs["GROQ_API_KEY"]      = $env:GROQ_API_KEY }
if ($env:OPENAI_API_KEY)    { $pairs["OPENAI_API_KEY"]    = $env:OPENAI_API_KEY }
if ($env:ANTHROPIC_API_KEY) { $pairs["ANTHROPIC_API_KEY"] = $env:ANTHROPIC_API_KEY }

$envFile = New-TemporaryFile
$lines = foreach ($k in $pairs.Keys) {
    # ConvertTo-Json yields a valid YAML double-quoted scalar with proper escaping.
    "${k}: $($pairs[$k] | ConvertTo-Json -Compress)"
}
Set-Content -Path $envFile -Value $lines -Encoding ascii

try {
    Write-Host "==> Deploying $SERVICE_NAME to Cloud Run"
    gcloud run deploy $SERVICE_NAME `
        --project $GCP_PROJECT `
        --region $GCP_REGION `
        --image $IMAGE `
        --platform managed `
        --allow-unauthenticated `
        --memory 512Mi `
        --cpu 1 `
        --min-instances 0 `
        --max-instances 4 `
        --concurrency 40 `
        --timeout 120s `
        --env-vars-file $envFile
    if ($LASTEXITCODE -ne 0) { throw "gcloud run deploy failed" }
}
finally {
    Remove-Item -Path $envFile -ErrorAction SilentlyContinue
}

$URL = gcloud run services describe $SERVICE_NAME `
    --project $GCP_PROJECT `
    --region $GCP_REGION `
    --format "value(status.url)"
Write-Host ""
Write-Host "==> Deployed: $URL"
Write-Host "    Set this in frontend/.env.production as VITE_API_BASE_URL,"
Write-Host "    and add to ALLOWED_ORIGINS on the next deploy if it changed."
