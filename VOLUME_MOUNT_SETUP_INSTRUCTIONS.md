# GCS Volume Mount Setup (generation/units/)

This document covers the one-time setup required to mount a GCS bucket at `/app/generation/units/` in the Cloud Run service. This replaces the previous approach of baking curriculum data into the Docker image — all working files (lesson folders, grounded sources, script.json, scenes, audio) now persist in GCS across container restarts and redeployments.

**Project**: `ai-tutor-dev-videos`
**Bucket**: `video-agent-generation-units`
**Service account**: `video-agent@ai-tutor-dev-videos.iam.gserviceaccount.com`
**Service name**: `video-agent`
**Region**: `us-central1`

---

## Prerequisites

- `gcloud` CLI installed and up to date — run `gcloud version` to confirm
- Authenticated to the correct project:
  ```bash
  gcloud auth login
  gcloud config set project ai-tutor-dev-videos
  ```
- The service must already be deployed at least once (so the service account identity exists)

---

## Step 1 — Create the GCS bucket

This bucket stores all working files — unit folders, grounded lesson sources, video script.json files, generated scenes, and audio. It is separate from `video-agent-artifacts` (which stores ADK session artifacts for download).

```bash
gcloud storage buckets create gs://video-agent-generation-units \
  --project=ai-tutor-dev-videos \
  --location=us-central1 \
  --uniform-bucket-level-access
```

### Verify it worked

```bash
gcloud storage buckets describe gs://video-agent-generation-units
```

You should see the bucket listed with `location: US-CENTRAL1`.

---

## Step 2 — Grant the service account access to the bucket

The Cloud Run service runs as `video-agent@ai-tutor-dev-videos.iam.gserviceaccount.com`. It needs `roles/storage.objectAdmin` on the working-files bucket so it can create, read, update, and delete files within it.

```bash
gcloud storage buckets add-iam-policy-binding gs://video-agent-generation-units \
  --member="serviceAccount:video-agent@ai-tutor-dev-videos.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

### Verify it worked

```bash
gcloud storage buckets get-iam-policy gs://video-agent-generation-units
```

You should see a binding like:

```
bindings:
- members:
  - serviceAccount:video-agent@ai-tutor-dev-videos.iam.gserviceaccount.com
  role: roles/storage.objectAdmin
```

---

## Step 3 — Add the volume mount to the Cloud Run service

This command attaches the GCS bucket as a volume at `/app/generation/units/` and sets `--max-instances=3` to cap scaling for this single-user tool.

```bash
gcloud run services update video-agent \
  --region us-central1 \
  --add-volume=name=generation-units,type=cloud-storage,bucket=video-agent-generation-units \
  --add-volume-mount=volume=generation-units,mount-path=/app/generation/units \
  --max-instances=3
```

> **Why `--max-instances=3`?** GCS FUSE mounts the same bucket on every instance, and GCS has been strongly consistent for read-after-write since 2021 — all instances see the same files. Multiple instances are safe. `3` gives enough headroom for simultaneous sessions (each uses 2 concurrent request slots: one SSE preview connection + agent turns) without unbounded scaling. The only residual risk is two pipeline runs writing to the exact same `unit/lesson/video` path simultaneously, which cannot happen in single-user usage.

### Verify the mount is configured

```bash
gcloud run services describe video-agent \
  --region us-central1 \
  --format="yaml(spec.template.spec.volumes, spec.template.spec.containers[0].volumeMounts)"
```

You should see a volume named `generation-units` with `cloudStorage.bucket: video-agent-generation-units` and a corresponding mount at `/app/generation/units`.

---

## Step 4 — Redeploy

Run the standard deployment command from `DEPLOY_INSTRUCTIONS.md` Step 4 to pick up the Dockerfile changes (removal of the `COPY generation/units/` line and addition of `RUN mkdir -p /app/generation/units`).

---

## Step 5 — Verify the mount is live

After deploy, start a session and ask the agent to ground a lesson:

```
"Make a video for aif1-v2-2025, lesson 2"
```

The agent will call `ground_lesson`, which creates the unit and lesson folder structure. Then check the bucket:

```bash
gcloud storage ls gs://video-agent-generation-units/
```

You should see a folder like `aif1-v2-2025/` appear. Drill in to confirm the lesson folder and `lesson-state.json` were created:

```bash
gcloud storage ls -r gs://video-agent-generation-units/aif1-v2-2025/
```

---

## Step 6 — (Recommended) Test persistence across restarts

To confirm files survive a container restart:

1. Run `ground_lesson` for a lesson and verify files appear in the bucket
2. Force a new container revision (re-deploy or wait for scale-to-zero — approximately 15 minutes of inactivity)
3. Start a new session and ask about the same lesson — `ground_lesson` should return `already_complete` without re-fetching

---

## Troubleshooting

### `Permission denied` when agent tries to write files

The service account is missing `objectAdmin` on the bucket. Re-run the Step 2 IAM command and wait ~30 seconds for propagation, then retry.

### Mount not appearing — files still missing after restart

The volume mount wasn't applied. Run the Step 3 `gcloud run services update` command again and check the Step 3 verification output. Make sure you see `volumeMounts` in the service spec.

### `Transport endpoint is not connected` errors in logs

This is a GCS FUSE mount failure — typically an IAM issue or the bucket doesn't exist. Confirm Step 1 (bucket exists) and Step 2 (IAM binding) are both correct.

### Container fails to start after adding the mount

Check that the `RUN mkdir -p /app/generation/units` line is present in the Dockerfile and the image was rebuilt and redeployed after adding it. GCS FUSE requires the mount point directory to exist in the container before it can attach.

### Files written in one session aren't visible in the next

Check that `--max-instances=1` is set on the service. If two instances were running simultaneously, one may have served a session with a stale view. With `max-instances=1`, this cannot happen.
