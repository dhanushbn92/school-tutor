#!/usr/bin/env bash
# Build the SPA and deploy it to Firebase Hosting.
#
# Required env vars (set before invoking, or in scripts/deploy.env):
#   VITE_API_BASE_URL   Cloud Run service URL the SPA should call
#   FIREBASE_PROJECT    Firebase project ID (also goes in frontend/.firebaserc)
#
# Prereqs: `npm install -g firebase-tools` and `firebase login` (one-time).

set -euo pipefail

if [[ -f "scripts/deploy.env" ]]; then
    # shellcheck disable=SC1091
    set -a; source scripts/deploy.env; set +a
fi

: "${VITE_API_BASE_URL:?VITE_API_BASE_URL is required}"
: "${FIREBASE_PROJECT:?FIREBASE_PROJECT is required}"

cd frontend

echo "==> Installing frontend deps (if needed)"
if [[ ! -d node_modules ]]; then
    npm install
fi

# Vite reads VITE_*-prefixed env vars from .env files OR the process env at
# build time. Exporting here ensures the value lands in the bundle even if
# .env.production isn't checked in.
export VITE_API_BASE_URL

echo "==> Building SPA against ${VITE_API_BASE_URL}"
npm run build

echo "==> Deploying to Firebase project ${FIREBASE_PROJECT}"
npx firebase deploy --only hosting --project "${FIREBASE_PROJECT}"
