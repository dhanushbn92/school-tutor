# Build the SPA and deploy it to Firebase Hosting.
#
# Required env vars (set before invoking, or in scripts/deploy.env.ps1):
#   VITE_API_BASE_URL   Cloud Run service URL the SPA should call
#   FIREBASE_PROJECT    Firebase project ID
#
# Prereqs: `npm install -g firebase-tools` and `firebase login` (one-time).

$ErrorActionPreference = "Stop"

if (Test-Path "scripts/deploy.env.ps1") {
    . "scripts/deploy.env.ps1"
}

if (-not $env:VITE_API_BASE_URL) { throw "VITE_API_BASE_URL is required" }
if (-not $env:FIREBASE_PROJECT)  { throw "FIREBASE_PROJECT is required" }

Push-Location frontend
try {
    if (-not (Test-Path node_modules)) {
        Write-Host "==> Installing frontend deps"
        npm install
        if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
    }

    Write-Host "==> Building SPA against $env:VITE_API_BASE_URL"
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "npm run build failed" }

    Write-Host "==> Deploying to Firebase project $env:FIREBASE_PROJECT"
    npx firebase deploy --only hosting --project $env:FIREBASE_PROJECT
    if ($LASTEXITCODE -ne 0) { throw "firebase deploy failed" }
}
finally {
    Pop-Location
}
