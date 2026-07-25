# Deploy: GCP Cloud Run + Firebase Hosting

This walks through deploying School Tutor end-to-end on the GCP free tier.

```
                      ┌────────────────────────┐
  Browser ────HTTPS──▶│  Firebase Hosting      │
                      │  (static SPA, /dist)   │
                      └──────────┬─────────────┘
                                 │  XHR (CORS)
                                 ▼
                      ┌────────────────────────┐
                      │  Cloud Run             │
                      │  school-tuter-api      │ ──▶ Supabase Postgres
                      │  (FastAPI container)   │ ──▶ GCS bucket (artifacts)
                      └────────────────────────┘
```

- **Firebase Hosting** — free 10 GB egress / month, global CDN, custom domain.
- **Cloud Run** — free 2M requests / 360k vCPU-seconds per month, scales to zero.
- **GCS** — free 5 GB-month standard storage in `us` regions.
- **Supabase** — free 500 MB Postgres + auth (already in use; unchanged).

---

## 0. One-time prerequisites

Install:

- `gcloud` CLI: <https://cloud.google.com/sdk/docs/install>
- `firebase` CLI: `npm install -g firebase-tools`
- Docker (for local image builds; optional — Cloud Build can do it remotely)

Authenticate:

```bash
gcloud auth login
gcloud auth application-default login   # for local GCS reads/writes
firebase login
```

---

## 1. Create the GCP project + APIs

```bash
# Pick a unique project ID.
gcloud projects create school-tuter-prod --name="School Tutor"
gcloud config set project school-tuter-prod
gcloud config set run/region asia-south1   # or your closest region

# Enable the services we use.
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    storage.googleapis.com
```

> **Billing must be enabled** on the project even for free-tier usage —
> Cloud Run will refuse to deploy otherwise. Free-tier quotas mean you pay
> nothing until you exceed them.

---

## 2. Artifact Registry (container images)

```bash
gcloud artifacts repositories create school-tuter \
    --repository-format=docker \
    --location=asia-south1 \
    --description="School Tutor container images"

# Allow `docker push` from your machine (only needed if you build locally).
gcloud auth configure-docker asia-south1-docker.pkg.dev
```

---

## 3. Cloud Storage bucket (artifacts)

Cloud Run is stateless — generated PDFs, PPTs, SVGs, and HTML simulations
must live outside the container. We bind one bucket per environment.

```bash
gcloud storage buckets create gs://school-tuter-artifacts \
    --location=asia-south1 \
    --uniform-bucket-level-access

# Grant the Cloud Run runtime service account read/write access.
PROJECT_NUMBER=$(gcloud projects describe school-tuter-prod --format='value(projectNumber)')
SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
gcloud storage buckets add-iam-policy-binding gs://school-tuter-artifacts \
    --member="serviceAccount:${SA}" \
    --role="roles/storage.objectAdmin"
```

> If you create a dedicated service account for Cloud Run, grant
> `roles/storage.objectAdmin` to that one instead and pass it via
> `gcloud run deploy --service-account=...`.

---

## 4. Database

You can keep using **Supabase** (recommended — it's already wired up). Just
copy the Postgres connection string from the Supabase dashboard and use
the SQLAlchemy psycopg URL form:

```
postgresql+psycopg://postgres.<ref>:<PASSWORD>@<HOST>:5432/postgres?sslmode=require
```

Run migrations once before the first deploy (and after every schema change):

```bash
# From your dev machine, against the prod DB:
DATABASE_URL='postgresql+psycopg://...?sslmode=require' \
  alembic upgrade head
```

---

## 5. Configure deploy env

Copy the example and fill in real values. The deploy scripts auto-source it.

```bash
cp scripts/deploy.env.example scripts/deploy.env
# edit scripts/deploy.env
```

PowerShell users:

```powershell
Copy-Item scripts/deploy.env.ps1.example scripts/deploy.env.ps1
# edit scripts/deploy.env.ps1
```

> `scripts/deploy.env` and `.env.production` are in `.gitignore` — keep them
> off of git.

---

## 6. Deploy the backend (Cloud Run)

```bash
bash scripts/deploy_cloud_run.sh
```

PowerShell:

```powershell
./scripts/deploy_cloud_run.ps1
```

The script:

1. `gcloud builds submit` — Cloud Build packs the repo using `Dockerfile`,
   pushes the image to Artifact Registry.
2. `gcloud run deploy` — rolls out a new revision with all env vars wired:
   - `ARTIFACT_BACKEND=gcs`
   - `GCS_BUCKET`, `DATABASE_URL`, `JWT_SECRET`, `ALLOWED_ORIGINS`
   - LLM provider keys (whichever you set)
   - `AUTO_CREATE_TABLES=false` — Alembic owns the schema in prod.
3. Prints the resulting service URL — e.g.
   `https://school-tuter-api-xxx.a.run.app`. Save it.

---

## 7. Deploy the frontend (Firebase Hosting)

One-time:

```bash
cd frontend
# Edit .firebaserc → set "default" to your Firebase project ID.
# (You can create the project at https://console.firebase.google.com — pick the
# same GCP project so billing/quotas stay aligned.)
```

Then, on every deploy:

```bash
# From repo root:
export VITE_API_BASE_URL=https://school-tuter-api-xxx.a.run.app
export FIREBASE_PROJECT=school-tuter
bash scripts/deploy_firebase.sh
```

PowerShell:

```powershell
$env:VITE_API_BASE_URL = "https://school-tuter-api-xxx.a.run.app"
$env:FIREBASE_PROJECT  = "school-tuter"
./scripts/deploy_firebase.ps1
```

Firebase prints the hosting URL — `https://<project>.web.app`. Open it.

---

## 8. Wire CORS

The backend's CORS allow-list is whatever you put in `ALLOWED_ORIGINS` on
the previous Cloud Run deploy. After Firebase gives you the hosting URLs,
update `scripts/deploy.env` so it includes them, then re-run
`scripts/deploy_cloud_run.sh`:

```
ALLOWED_ORIGINS=https://school-tuter.web.app,https://school-tuter.firebaseapp.com,https://school-tutor-hub.web.app,https://school-tutor-hub.firebaseapp.com
```

> If you bind a custom domain (e.g. `app.example.com`), add it to
> `ALLOWED_ORIGINS` and redeploy the backend.

---

## 9. Smoke test

```bash
# Health check
curl https://school-tuter-api-xxx.a.run.app/health

# Open the SPA
open https://school-tuter.web.app
```

Sign up, take a quiz, generate content. Check that:

- Generated PDFs/PPTs download (proves GCS is wired correctly).
- AI tutor chat works (proves Anthropic / Groq key reached the container).
- Logs show no `CORS` rejections in the browser console.

---

## Per-deploy summary (after first-time setup)

```bash
# Schema change?
DATABASE_URL=... alembic upgrade head

# Backend
bash scripts/deploy_cloud_run.sh

# Frontend
bash scripts/deploy_firebase.sh
```

---

## Troubleshooting

**`google.auth.exceptions.DefaultCredentialsError` locally**
Run `gcloud auth application-default login` once. On Cloud Run the runtime
service account is picked up automatically.

**`403 storage.objects.create`**
The Cloud Run service account doesn't have write access to the bucket.
Re-run the IAM binding from step 3, double-checking the service account
matches what's bound to the Cloud Run service
(`gcloud run services describe school-tuter-api --format='value(spec.template.spec.serviceAccountName)'`).

**`OperationalError: SSL connection has been closed unexpectedly`**
Append `?sslmode=require` to `DATABASE_URL`. Supabase requires SSL.

**SPA shows blank page / 404 on refresh**
Confirm `frontend/firebase.json` has the `**` → `/index.html` rewrite. Without
it, Firebase Hosting serves a 404 for client-side routes.

**`alembic upgrade head` fails with `relation already exists`**
The first deploy may have run with `AUTO_CREATE_TABLES=true`, which lets
SQLAlchemy create tables that Alembic doesn't know about. Stamp the
baseline once: `alembic stamp head`, then run normal migrations going
forward. Make sure prod is set to `AUTO_CREATE_TABLES=false` (the deploy
script already does this).

**Cold-start latency**
Cloud Run scales to zero. First request after idle takes ~2–4s. Set
`--min-instances=1` on the deploy command if you need always-warm
(this leaves the free tier — ~$5/month).
