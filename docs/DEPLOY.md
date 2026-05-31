# Deploy — backend + frontend to Google Cloud Run

## How CI/CD works

- **PRs / feature branches** → `backend.yml` + `frontend.yml` run tests only (unchanged).
- **Merge to `planning`** → `deploy.yml` builds the backend + frontend Docker images,
  pushes them to **GHCR**, mirrors them to **Artifact Registry**, and deploys both to
  **Cloud Run**.

`deploy.yml` is **dormant** until you set the repo variable `DEPLOY_ENABLED=true`. Until
then it's skipped (planning stays green). Enable it only after the setup below and after
confirming the images build.

## Architecture

- Backend (FastAPI) → Cloud Run service `umraa-backend` (port 8080)
- Frontend (Next.js, `output: standalone`) → Cloud Run service `umraa-frontend` (port 8080)
- DB: seeded-local for now (no Cloud SQL yet — PRD §22 primary demo path is local)
- Images: published to GHCR; Cloud Run pulls from Artifact Registry (mirrored in CI)

## One-time GCP setup (owner: Hamza)

1. Pick/create a GCP project; note the **project ID** and a **region** (e.g. `us-central1`).
2. Enable APIs:
   ```bash
   gcloud services enable run.googleapis.com artifactregistry.googleapis.com --project <PROJECT_ID>
   ```
3. Create the Artifact Registry repo named `umraa`:
   ```bash
   gcloud artifacts repositories create umraa --repository-format=docker \
     --location <REGION> --project <PROJECT_ID>
   ```
4. Create a deploy service account + grant roles:
   ```bash
   gcloud iam service-accounts create umraa-deployer --project <PROJECT_ID>
   SA="umraa-deployer@<PROJECT_ID>.iam.gserviceaccount.com"
   for role in roles/run.admin roles/artifactregistry.writer roles/iam.serviceAccountUser; do
     gcloud projects add-iam-policy-binding <PROJECT_ID> --member="serviceAccount:$SA" --role="$role"
   done
   gcloud iam service-accounts keys create key.json --iam-account "$SA"
   ```

## GitHub config

Repo **Secrets** (Settings → Secrets and variables → Actions → Secrets):
- `GCP_SA_KEY` — paste the full contents of `key.json` (then delete the local file)
- `GCP_PROJECT_ID` — the project ID

Repo **Variables** (… → Variables):
- `DEPLOY_ENABLED` = `true`  (turns the pipeline on)
- `GCP_REGION` = e.g. `us-central1`
- `NEXT_PUBLIC_API_BASE_URL` = the backend Cloud Run URL (set after the first backend deploy, then re-run to bake it into the frontend)

## Notes

- `NEXT_PUBLIC_*` is baked at build time. First deploy backend → copy its Cloud Run URL into
  the `NEXT_PUBLIC_API_BASE_URL` variable → next merge rebuilds the frontend against it.
- `key.json` is a long-lived secret — keep it only in the GitHub secret, never in the repo.
- Local dev unchanged: `docker compose up` (Postgres) + `uvicorn backend.app.main:app` + `npm run dev`.
