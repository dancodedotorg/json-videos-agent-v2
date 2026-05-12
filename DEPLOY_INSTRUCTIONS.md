# Cloud Run Deployment Instructions

This document covers everything needed to deploy the video generation agent to Google Cloud Run and wire it into IAP.

**Project**: `ai-tutor-dev-videos`
**Region**: `us-central1`
**Service name**: `video-agent`

---

## Prerequisites

### Tools needed on your machine
- `gcloud` CLI — [install guide](https://cloud.google.com/sdk/docs/install)
- Docker Desktop (optional — only needed for local smoke testing; NOT required for Cloud Run deployment)

If on WSL2, Docker requires enabling **WSL Integration** in Docker Desktop settings (Settings → Resources → WSL Integration).

### Check gcloud is installed and up to date
```bash
gcloud version
gcloud components update
```

---

## Step 1 — One-Time GCP Setup

These steps only need to be done once per project.

### 1a. Authenticate and set project
```bash
gcloud auth login
gcloud config set project ai-tutor-dev-videos
```

### 1b. Enable required APIs
```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com
```

### 1c. Grant Cloud Build permission to the default compute service account

`gcloud run deploy --source .` uses Cloud Build to build the image. Cloud Build runs as the default compute service account and needs permission to push to Artifact Registry.

```bash
PROJECT_NUMBER=$(gcloud projects describe ai-tutor-dev-videos --format="value(projectNumber)")

gcloud projects add-iam-policy-binding ai-tutor-dev-videos \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/cloudbuild.builds.builder"
```

---

## Step 2 — Create the Environment Variables File

The deployment needs your API credentials. Rather than typing them on the command line (especially for the long service account JSON), create a local YAML file that `gcloud` will read.

### 2a. Create `cloud-run-env.yaml` at the project root

```bash
touch cloud-run-env.yaml
```

Open it and paste in the following, filling in values from `generation/tools/.env`:

```yaml
GOOGLE_API_KEY: "your_google_api_key_here"
ELEVENLABS_API_KEY: "your_elevenlabs_api_key_here"
GOOGLE_SERVICE_ACCOUNT_JSON: "your_base64_encoded_service_account_json_here"
GOOGLE_GENAI_USE_VERTEXAI: "False"
```

The values for all three secrets are already in `generation/tools/.env`:
- `GOOGLE_API_KEY` — the `AIzaSy...` string
- `ELEVENLABS_API_KEY` — the `sk_...` string
- `GOOGLE_SERVICE_ACCOUNT_JSON` — the long `ewogIC...` base64 string

### 2b. Make sure `cloud-run-env.yaml` is gitignored

Add it to `.gitignore` if it isn't already:

```bash
echo "cloud-run-env.yaml" >> .gitignore
```

> **Important**: Never commit this file — it contains live production credentials.

---

## Step 3 — (Optional) Local Docker Smoke Test

> Skip this section if Docker Desktop isn't set up. Cloud Run deployment does not require local Docker — it builds the image remotely via Cloud Build.

If you do have Docker Desktop running with WSL integration enabled:

### 3a. Build the image
```bash
docker build -t video-agent-test .
```

This will take a few minutes on the first run (installing Python packages). Subsequent builds are faster due to layer caching.

### 3b. Run locally
```bash
docker run -p 8080:8080 \
  -e PORT=8080 \
  -e GOOGLE_API_KEY="your_key" \
  -e ELEVENLABS_API_KEY="your_key" \
  -e GOOGLE_SERVICE_ACCOUNT_JSON="your_base64_json" \
  -e GOOGLE_GENAI_USE_VERTEXAI=False \
  video-agent-test
```

### 3c. Verify the server is up
```bash
curl http://localhost:8080/list-apps
```

Expected response: `["backend"]`

Open `http://localhost:8080` in a browser — you should see the ADK web UI with `video_generation_agent` in the dropdown.

---

## Step 4 — Deploy to Cloud Run

Run this from the **project root** (where the `Dockerfile` lives). Cloud Build uploads your source, builds the image remotely, and deploys it — no local Docker required.

```bash
gcloud run deploy video-agent \
  --source . \
  --region us-central1 \
  --project ai-tutor-dev-videos \
  --no-allow-unauthenticated \
  --timeout=600 \
  --concurrency=1 \
  --memory=2Gi \
  --env-vars-file cloud-run-env.yaml
```

### What happens during deployment
1. Your source is uploaded to Cloud Storage
2. Cloud Build builds the Docker image using your `Dockerfile`
3. The image is pushed to Artifact Registry
4. Cloud Run deploys a new revision and switches traffic to it

### Prompts to expect
- **`Create Artifact Registry repository?`** → `y`
- **`Allow unauthenticated invocations?`** → `N` (IAP handles auth)

### How long it takes
- First deploy: ~5–8 minutes (pip install is the slow part; it's cached on subsequent deploys if requirements.txt hasn't changed)
- Re-deploys without requirements changes: ~2–3 minutes

### Get the service URL when done
```bash
gcloud run services describe video-agent \
  --region us-central1 \
  --format="value(status.url)"
```

This URL (`https://video-agent-xxx-uc.a.run.app`) is the **internal Cloud Run URL**. It will return 403 if accessed directly — that's expected. Users access the service through IAP (see Step 5).

---

## Step 5 — Wire into IAP

Since you have IAP already configured on a load balancer, you need to add this Cloud Run service as a backend.

### 5a. Create a Serverless NEG for the Cloud Run service

A Serverless Network Endpoint Group (NEG) tells the load balancer where to find the Cloud Run service.

```bash
gcloud compute network-endpoint-groups create video-agent-neg \
  --region=us-central1 \
  --network-endpoint-type=serverless \
  --cloud-run-service=video-agent \
  --project=ai-tutor-dev-videos
```

### 5b. Add the NEG as a backend to your existing backend service

Replace `YOUR_BACKEND_SERVICE_NAME` with the name of your existing IAP-protected backend service:

```bash
gcloud compute backend-services add-backend YOUR_BACKEND_SERVICE_NAME \
  --network-endpoint-group=video-agent-neg \
  --network-endpoint-group-region=us-central1 \
  --global
```

### 5c. Add a URL map rule to route traffic to the agent

If your load balancer hosts multiple services at different paths, add a path matcher rule pointing `/video-agent/*` (or whatever path you want) to the backend service containing the video-agent NEG.

If the agent gets its own dedicated load balancer frontend, no URL map rule is needed.

### 5d. Grant IAP permission to invoke the Cloud Run service

IAP uses a managed service account to call Cloud Run on behalf of authenticated users. Grant it the `roles/run.invoker` role:

```bash
gcloud run services add-iam-policy-binding video-agent \
  --region=us-central1 \
  --member="serviceAccount:service-$(gcloud projects describe ai-tutor-dev-videos --format='value(projectNumber)')@gcp-sa-iap.iam.gserviceaccount.com" \
  --role="roles/run.invoker" \
  --project=ai-tutor-dev-videos
```

### 5e. Test via IAP URL

Once wired in, open the IAP-fronted URL in your browser. IAP will redirect to Google sign-in if you're not already authenticated.

---

## Step 6 — Verify the Deployment

### Quick API check (authenticated)
```bash
SERVICE_URL=$(gcloud run services describe video-agent \
  --region us-central1 \
  --format="value(status.url)")

TOKEN=$(gcloud auth print-identity-token)

curl -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/list-apps"
```

Expected: `["backend"]`

### Full smoke test
1. Open the IAP URL in a browser
2. Select `backend` from the agent dropdown
3. Start a new session
4. Type: `What videos are set up for aif1-v2-2025?`
5. The agent should respond by listing available lessons/videos from the baked-in snapshot

---

## Redeploying

### Redeploy with code changes only
```bash
gcloud run deploy video-agent \
  --source . \
  --region us-central1 \
  --project ai-tutor-dev-videos \
  --no-allow-unauthenticated \
  --timeout=600 \
  --concurrency=1 \
  --memory=2Gi \
  --env-vars-file cloud-run-env.yaml
```

Cloud Run creates a new revision and switches traffic to it with zero downtime.

### Redeploy with an updated `generation/units/` snapshot

After grounding new lessons locally (running `/lesson-ground` via `adk web`), redeploy using the same command above. The `Dockerfile` copies `generation/units/` at build time, so the new snapshot is baked into the new image automatically.

> **Tip**: The pip install layer is cached as long as `backend/requirements.txt` hasn't changed. If you haven't touched requirements, the rebuild skips the slow install step and is much faster.

---

## Viewing Logs

```bash
gcloud run services logs read video-agent \
  --region us-central1 \
  --limit 50
```

Or stream live:
```bash
gcloud run services logs tail video-agent \
  --region us-central1
```

Or open Cloud Logging in the console:
[console.cloud.google.com/run](https://console.cloud.google.com/run) → `video-agent` → Logs tab

---

## Updating Environment Variables Without a Full Redeploy

If you need to rotate a key without redeploying from source, update the env vars directly:

```bash
gcloud run services update video-agent \
  --region us-central1 \
  --env-vars-file cloud-run-env.yaml
```

This creates a new revision with the updated env vars in about 30 seconds — no image rebuild.

---

## Troubleshooting

### `list-apps` returns `[]` instead of `["backend"]`
The agent module wasn't discovered. Check that `backend/__init__.py` contains `from . import agent`. Verify with:
```bash
TOKEN=$(gcloud auth print-identity-token)
curl -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/list-apps"
```

### Agent starts but skills aren't available
The skills directory wasn't found. Confirm `backend/skills/` exists in the container by checking the build logs in Cloud Build console.

### 403 on the Cloud Run URL directly
Expected — the service is private. Access through your IAP URL, not the `*.run.app` URL directly.

### Timeout during audio generation
If ElevenLabs or Gemini audio takes longer than expected, Cloud Run will kill the request at 600s (10 min). This shouldn't happen given normal usage, but if it does, check ElevenLabs API status.

### Container fails to start (check logs)
```bash
gcloud run services logs read video-agent --region us-central1 --limit 20
```
Common causes: missing env var, import error in agent.py (check for syntax errors), or a missing package in requirements.txt.
