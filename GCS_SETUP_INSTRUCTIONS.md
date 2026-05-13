# GCS Artifact Bucket Setup

This document covers the one-time setup required to let the Cloud Run service store and retrieve artifacts from the GCS bucket `video-agent-artifacts`.

**Project**: `ai-tutor-dev-videos`
**Bucket**: `video-agent-artifacts`
**Service account**: `video-agent@ai-tutor-dev-videos.iam.gserviceaccount.com`

---

## Prerequisites

- `gcloud` CLI installed and up to date — run `gcloud version` to confirm
- Authenticated to the correct project:
  ```bash
  gcloud auth login
  gcloud config set project ai-tutor-dev-videos
  ```

---

## Step 1 — Enable the Cloud Storage API

Cloud Storage must be enabled on the project before anything else works. This is a one-time step — if you've already used GCS in this project, it's already enabled and you can skip to Step 2.

```bash
gcloud services enable storage.googleapis.com --project ai-tutor-dev-videos
```

---

## Step 2 — Grant the service account access to the bucket

When Cloud Run runs the agent, it authenticates as a **service account** — a non-human identity that represents the application. By default this service account has no access to GCS buckets, so we need to explicitly grant it permission to read and write objects in `video-agent-artifacts`.

The permission level we're granting is `roles/storage.objectAdmin`, which allows the service account to create, read, list, and delete objects within the bucket — exactly what the ADK artifact service needs.

```bash
gcloud storage buckets add-iam-policy-binding gs://video-agent-artifacts \
  --member="serviceAccount:video-agent@ai-tutor-dev-videos.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

### Verify it worked

```bash
gcloud storage buckets get-iam-policy gs://video-agent-artifacts
```

You should see a binding like:

```
bindings:
- members:
  - serviceAccount:video-agent@ai-tutor-dev-videos.iam.gserviceaccount.com
  role: roles/storage.objectAdmin
```

---

## Step 3 — Add `ARTIFACT_BUCKET` to your env file

Open `cloud-run-env.yaml` at the project root and add this line:

```yaml
ARTIFACT_BUCKET: "video-agent-artifacts"
```

Your full `cloud-run-env.yaml` should now look like:

```yaml
GOOGLE_API_KEY: "your_google_api_key_here"
ELEVENLABS_API_KEY: "your_elevenlabs_api_key_here"
GOOGLE_SERVICE_ACCOUNT_JSON: "your_base64_encoded_service_account_json_here"
GOOGLE_GENAI_USE_VERTEXAI: "False"
ARTIFACT_BUCKET: "video-agent-artifacts"
```

This file is gitignored — it lives only on your machine.

---

## Step 4 — Redeploy

Run the standard deployment command from `DEPLOY_INSTRUCTIONS.md` Step 4. If you have also completed `SQL_SETUP_INSTRUCTIONS.md`, use the full command with `--add-cloudsql-instances`; otherwise omit that flag.

---

## Step 5 — Verify

### Check Cloud Run logs

After deploy, tail the logs and look for confirmation that GCS is in use:

```bash
gcloud run services logs tail video-agent --region us-central1
```

You should see a message referencing `GcsArtifactService` or `gs://video-agent-artifacts`. You should **not** see `InMemoryArtifactService`.

### Run a full smoke test

1. Open the IAP URL in a browser
2. Start a new session with `video_generation_agent`
3. Run through a video generation pipeline to completion
4. When `save_video_output` runs, confirm no "failed to fetch artifact" error appears in the UI
5. Check the GCS console: [console.cloud.google.com/storage/browser/video-agent-artifacts](https://console.cloud.google.com/storage/browser/video-agent-artifacts) — you should see blobs under a `backend/` prefix

---

## Step 6 — (Recommended) Set a lifecycle rule

ADK stores artifact versions as separate blobs but never deletes old ones. Without a cleanup rule the bucket will accumulate files indefinitely. The rule below deletes any object older than 30 days.

### Create `lifecycle.json`

```json
{
  "lifecycle": {
    "rule": [
      {
        "action": { "type": "Delete" },
        "condition": { "age": 30 }
      }
    ]
  }
}
```

### Apply it to the bucket

```bash
gcloud storage buckets update gs://video-agent-artifacts \
  --lifecycle-file=lifecycle.json
```

Adjust `age` if you need artifacts to remain accessible for longer (e.g. `90` for three months).

---

## Troubleshooting

### `403 Permission denied` in Cloud Run logs

The service account doesn't have bucket access yet. Re-run the Step 2 `add-iam-policy-binding` command and redeploy.

### Artifacts still use InMemory after deploy

`ARTIFACT_BUCKET` wasn't picked up. Check:
1. The variable is present in `cloud-run-env.yaml` with no typos
2. You redeployed **after** updating the file (env vars are baked into the revision at deploy time, not read dynamically)
3. Run `gcloud run services describe video-agent --region us-central1 --format="yaml(spec.template.spec.containers[0].env)"` to confirm the env var is set on the live revision

### "failed to fetch artifact" still appears

The IAM binding is missing or the `ARTIFACT_BUCKET` env var is wrong. Check the Cloud Run logs for any storage errors during the `save_artifact` call, then verify the bucket name matches exactly (`video-agent-artifacts`).
