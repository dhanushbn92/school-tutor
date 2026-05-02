# CI/CD setup — push-to-main automatic deploys

Two GitHub Actions workflows ship this repo to production:

* `.github/workflows/deploy-backend.yml`  → Cloud Run (FastAPI image)
* `.github/workflows/deploy-frontend.yml` → Firebase Hosting (Vite SPA)

Each is path-filtered so a frontend-only PR doesn't redeploy the
backend, and vice versa. Both also accept `workflow_dispatch` so you
can re-run them manually from the Actions tab.

This document is the **one-time setup** to authorise the workflows
against your GCP project and Firebase site. After it's done, every
push to `main` deploys automatically.

---

## 1. GCP — Workload Identity Federation (recommended)

WIF lets the GitHub Actions runner mint a short-lived OIDC token that
GCP exchanges for a service-account access token. **No static
credentials in GitHub.** The setup is one-time per repo.

### One-time GCP setup

Run this once in Cloud Shell (or a workstation with `gcloud` and admin
on the project). Substitute your actual values for the four
placeholders at the top:

```bash
PROJECT_ID="school-tuter-prod"
GITHUB_REPO="dhanushbn92/school-tutor"   # owner/repo
WIF_POOL="github-pool"
WIF_PROVIDER="github"

gcloud config set project "$PROJECT_ID"
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')

# 1. Enable the APIs the workflow needs.
gcloud services enable \
  iamcredentials.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com

# 2. Service account that the workflow assumes.
gcloud iam service-accounts create github-deployer \
  --display-name "GitHub Actions deployer"
SA_EMAIL="github-deployer@$PROJECT_ID.iam.gserviceaccount.com"

# 3. Roles the SA needs to deploy to Cloud Run + push to AR.
for role in \
  roles/run.admin \
  roles/iam.serviceAccountUser \
  roles/artifactregistry.writer \
  roles/storage.objectAdmin
do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" --role="$role"
done

# 4. Workload Identity Pool + Provider.
gcloud iam workload-identity-pools create "$WIF_POOL" \
  --location=global --display-name="GitHub pool"

gcloud iam workload-identity-pools providers create-oidc "$WIF_PROVIDER" \
  --location=global \
  --workload-identity-pool="$WIF_POOL" \
  --display-name="GitHub provider" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
  --attribute-condition="assertion.repository_owner == '$(echo $GITHUB_REPO | cut -d/ -f1)'"

# 5. Allow the SA to be impersonated by tokens from this exact repo only.
gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$WIF_POOL/attribute.repository/$GITHUB_REPO"

# 6. Print the two values you'll paste into GitHub Secrets.
echo
echo "Add these to GitHub > Settings > Secrets and variables > Actions:"
echo "  GCP_WORKLOAD_IDENTITY_PROVIDER = projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$WIF_POOL/providers/$WIF_PROVIDER"
echo "  GCP_SERVICE_ACCOUNT            = $SA_EMAIL"
```

The `attribute-condition` on step 4 is the security boundary: only OIDC
tokens whose `repository_owner` claim matches yours can use this
provider. Anyone else's GitHub Actions cannot.

---

## 2. Firebase — service account JSON

There's no WIF equivalent for Firebase Hosting deploys today, so we use
a service-account JSON. It's a long-lived credential — keep it in a
GitHub Secret only, never in the repo.

```bash
PROJECT_ID="school-tuter"   # your Firebase project ID

# 1. Enable IAM API on the Firebase project (usually already on).
gcloud services enable iam.googleapis.com --project "$PROJECT_ID"

# 2. Service account just for hosting deploys.
gcloud iam service-accounts create firebase-hosting-deployer \
  --project "$PROJECT_ID" \
  --display-name "Firebase Hosting deployer"

SA="firebase-hosting-deployer@$PROJECT_ID.iam.gserviceaccount.com"

# 3. Minimum role for hosting deploys.
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$SA" \
  --role="roles/firebasehosting.admin"

# 4. Generate the JSON key.
gcloud iam service-accounts keys create firebase-key.json \
  --iam-account "$SA"

# 5. Print the JSON (paste the WHOLE thing, including braces, into the
#    FIREBASE_SERVICE_ACCOUNT GitHub secret) and then delete the file.
cat firebase-key.json
rm firebase-key.json
```

---

## 3. GitHub Secrets to set

Settings → Secrets and variables → Actions → **New repository secret**.
You can paste these in any order. Names must match exactly.

| Secret | Source | Notes |
|---|---|---|
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Output of step 1.6 | `projects/.../providers/github` |
| `GCP_SERVICE_ACCOUNT`            | Output of step 1.6 | `github-deployer@...iam.gserviceaccount.com` |
| `GCP_PROJECT`                    | Your project ID | e.g. `school-tuter-prod` |
| `GCP_REGION`                     | Cloud Run region | e.g. `asia-south1` |
| `GCP_AR_REPO`                    | Artifact Registry repo name | e.g. `school-tuter` |
| `GCP_SERVICE_NAME`               | Cloud Run service name | e.g. `school-tuter-api` |
| `GCS_BUCKET`                     | Artifact bucket | e.g. `school-tuter-artifacts` |
| `DATABASE_URL`                   | Production Postgres | `postgresql+psycopg://USER:PASS@HOST:5432/DB?sslmode=require` |
| `JWT_SECRET`                     | Long random string | Same value the running service uses today |
| `ALLOWED_ORIGINS`                | Frontend URLs | `https://school-tuter.web.app,https://school-tuter.firebaseapp.com` |
| `LLM_PROVIDER`                   | `anthropic`, `groq`, or `openai` |  |
| `ANTHROPIC_API_KEY`              | If using Anthropic | Otherwise leave blank |
| `GROQ_API_KEY`                   | If using Groq |  |
| `OPENAI_API_KEY`                 | If using OpenAI |  |
| `FIREBASE_PROJECT`               | Firebase project ID | e.g. `school-tuter` |
| `FIREBASE_SERVICE_ACCOUNT`       | Output of step 2.5 | The full JSON, braces included |
| `VITE_API_BASE_URL`              | Cloud Run URL | e.g. `https://school-tuter-api-xxx.a.run.app` |

You almost certainly already have the production values in
`scripts/deploy.env` — copy from there.

---

## 4. (Strongly recommended) GitHub deployment environment

Both workflows declare `environment: production`. If you create that
environment in the repo settings, GitHub will:

* Show every deploy against it in the Environments tab (clickable history).
* Optionally require **manual approval** before the workflow runs (one
  click from a reviewer; great safety net for prod).
* Optionally restrict to specific branches (so only `main` can deploy).

Setup: Settings → Environments → **New environment** → name it
`production`. Tick "Required reviewers" if you want approval gating.

If you skip this, the workflows still run — the `environment:` line is
just a no-op label.

---

## 5. First-time validation

The workflows use `workflow_dispatch` so you can trigger them manually
from the Actions tab without committing anything new:

1. Push the `chore/cicd` branch (or however you named it) so GitHub
   sees the workflow files.
2. Open the repo → Actions tab.
3. Pick **"Deploy backend (Cloud Run)"** → "Run workflow" → choose the
   `chore/cicd` branch → Run. Watch the steps.
4. If it succeeds, do the same for **"Deploy frontend (Firebase
   Hosting)"**.
5. Once both pass on the side branch, merge `chore/cicd` to `main`.
   From then on, every push to `main` that touches the relevant paths
   deploys automatically.

If a manual run fails, the step that died will tell you which secret
or which permission is missing — fix that one thing, re-run.

---

## 6. Day-to-day operation

* **Normal flow**: push to a feature branch → open a PR → review →
  merge to main → deploy fires.
* **Hotfix**: push directly to main (if your branch protection allows
  it) — deploy fires.
* **Re-deploy without a code change**: Actions tab → workflow → Run
  workflow.
* **Rollback**: Cloud Run keeps every revision. Either run the
  workflow against an older commit (`Run workflow` lets you pick a
  branch / SHA) or use the existing
  `gcloud run services update-traffic ... --to-revisions=...` command.
  Firebase Hosting: `firebase hosting:rollback`.

---

## 7. Why not just call the existing `deploy_*.ps1` scripts from CI?

Tempting, but the existing scripts are PowerShell-Windows specific
(they read `$env:VAR` syntax) and depend on the populated
`scripts/deploy.env.ps1` which is **not** in the repo (gitignored, as
it should be — it has secrets). Running them on Linux runners would
need a translation step, plus we'd still need to inject all the same
secrets from GitHub. Net: writing the workflows directly with the
official Google + Firebase actions is shorter, more idiomatic for
GitHub Actions, and uses better-supported tools.

The local `.ps1` scripts continue to work for dev / break-glass
deploys from your workstation. Both paths can coexist.
