# Cloud SQL Session Database Setup

This document covers the one-time setup required to give the Cloud Run service a persistent PostgreSQL session store using Cloud SQL. Without this, each Cloud Run instance uses an in-process SQLite file that disappears on restart, causing session loss when the container is replaced or scaled.

**Project**: `ai-tutor-dev-videos`
**Cloud SQL instance**: `video-agent-sessions`
**Region**: `us-central1`
**Database**: `video_agent_sessions`
**DB user**: `video_agent`
**Service account**: `video-agent@ai-tutor-dev-videos.iam.gserviceaccount.com`

---

## How it works

Cloud Run has built-in Cloud SQL support. When you add `--add-cloudsql-instances` to a deploy command, Cloud Run mounts a Unix domain socket at `/cloudsql/PROJECT:REGION:INSTANCE` inside the container. The agent connects to PostgreSQL through that socket — no sidecar, no VPC, no public IP needed. The `CLOUDSQL_INSTANCE`, `DB_USER`, `DB_PASS`, and `DB_NAME` environment variables tell the app which socket and credentials to use.

`main.py` detects whether `CLOUDSQL_INSTANCE` is set. If yes, it routes sessions to PostgreSQL. If not (local dev), it falls back to the SQLite file.

---

## Prerequisites

- `gcloud` CLI installed and authenticated:
  ```bash
  gcloud auth login
  gcloud config set project ai-tutor-dev-videos
  ```

---

## Step 1 — Enable the Cloud SQL API

```bash
gcloud services enable sqladmin.googleapis.com --project ai-tutor-dev-videos
```

---

## Step 2 — Create the Cloud SQL instance

This creates a PostgreSQL 16 instance in the same region as Cloud Run. `db-g1-small` is the smallest available shared-core tier for the ENTERPRISE edition (~$10/month) and is sufficient for this low-traffic use case.

```bash
gcloud sql instances create video-agent-sessions \
  --database-version=POSTGRES_16 \
  --edition=ENTERPRISE \
  --tier=db-g1-small \
  --region=us-central1 \
  --project=ai-tutor-dev-videos
```

This takes 3–5 minutes. The instance will have a public IP by default (required for the socket-based Cloud Run connection).

### Verify it created successfully

```bash
gcloud sql instances describe video-agent-sessions \
  --project=ai-tutor-dev-videos \
  --format="value(state)"
```

Expected output: `RUNNABLE`

---

## Step 3 — Create the database and user

### 3a. Create the database

```bash
gcloud sql databases create video_agent_sessions \
  --instance=video-agent-sessions \
  --project=ai-tutor-dev-videos
```

### 3b. Create the database user

Choose a strong password and save it somewhere safe — you'll put it in `cloud-run-env.yaml` in Step 5.

```bash
gcloud sql users create video_agent \
  --instance=video-agent-sessions \
  --password=YOUR_STRONG_PASSWORD \
  --project=ai-tutor-dev-videos
```

Replace `YOUR_STRONG_PASSWORD` with a password that uses only letters, numbers, and underscores — special characters in the password can cause URL parsing issues.

### Verify the database and user exist

```bash
gcloud sql databases list --instance=video-agent-sessions --project=ai-tutor-dev-videos
gcloud sql users list --instance=video-agent-sessions --project=ai-tutor-dev-videos
```

---

## Step 4 — Grant the service account permission to connect

The Cloud Run service runs as `video-agent@ai-tutor-dev-videos.iam.gserviceaccount.com`. It needs `roles/cloudsql.client` to open connections through the Cloud Run socket.

```bash
gcloud projects add-iam-policy-binding ai-tutor-dev-videos \
  --member="serviceAccount:video-agent@ai-tutor-dev-videos.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"
```

### Verify it worked

```bash
gcloud projects get-iam-policy ai-tutor-dev-videos \
  --flatten="bindings[].members" \
  --filter="bindings.members:video-agent@ai-tutor-dev-videos.iam.gserviceaccount.com" \
  --format="table(bindings.role)"
```

You should see `roles/cloudsql.client` in the output (alongside any existing roles).

---

## Step 5 — Add credentials to your env file

Open `cloud-run-env.yaml` at the project root and add these four lines:

```yaml
CLOUDSQL_INSTANCE: "ai-tutor-dev-videos:us-central1:video-agent-sessions"
DB_USER: "video_agent"
DB_PASS: "your_db_password_here"
DB_NAME: "video_agent_sessions"
```

Your full `cloud-run-env.yaml` should now look like:

```yaml
GOOGLE_API_KEY: "your_google_api_key_here"
ELEVENLABS_API_KEY: "your_elevenlabs_api_key_here"
GOOGLE_SERVICE_ACCOUNT_JSON: "your_base64_encoded_service_account_json_here"
GOOGLE_GENAI_USE_VERTEXAI: "False"
ARTIFACT_BUCKET: "video-agent-artifacts"
CLOUDSQL_INSTANCE: "ai-tutor-dev-videos:us-central1:video-agent-sessions"
DB_USER: "video_agent"
DB_PASS: "your_db_password_here"
DB_NAME: "video_agent_sessions"
```

This file is gitignored — it lives only on your machine.

---

## Step 6 — Redeploy

The deploy command now includes `--add-cloudsql-instances`. Run the standard deployment command from `DEPLOY_INSTRUCTIONS.md` Step 4:

```bash
gcloud run deploy video-agent \
  --source . \
  --region us-central1 \
  --project ai-tutor-dev-videos \
  --no-allow-unauthenticated \
  --timeout=600 \
  --concurrency=1 \
  --memory=2Gi \
  --add-cloudsql-instances=ai-tutor-dev-videos:us-central1:video-agent-sessions \
  --env-vars-file cloud-run-env.yaml
```

The `--add-cloudsql-instances` flag tells Cloud Run to mount the PostgreSQL socket inside the container at `/cloudsql/ai-tutor-dev-videos:us-central1:video-agent-sessions`.

ADK automatically creates the session tables on first startup — no manual schema migration needed for a fresh database.

---

## Step 7 — Verify

### Check Cloud Run logs

```bash
gcloud run services logs tail video-agent --region us-central1
```

On startup you should **not** see any `Failed to create database engine` or `asyncpg` errors. A clean startup with no database errors means the connection succeeded.

### Confirm sessions persist across requests

1. Open the IAP URL in a browser
2. Start a new session and send a few messages
3. Note the session ID in the URL or UI
4. In a separate terminal, update the service (e.g. `gcloud run services update video-agent --region us-central1 --env-vars-file cloud-run-env.yaml`) to force a new revision
5. Reload the browser — the previous session should still be accessible

### Inspect the database (optional)

If you want to confirm ADK created its tables:

```bash
gcloud sql connect video-agent-sessions \
  --user=video_agent \
  --database=video_agent_sessions \
  --project=ai-tutor-dev-videos
```

Then in the psql prompt:

```sql
\dt
```

You should see tables like `sessions`, `events`, and `app_states` (exact names depend on the ADK version).

---

## Troubleshooting

### `connection refused` or `asyncpg` error on startup

The `CLOUDSQL_INSTANCE` env var is set but Cloud Run wasn't deployed with `--add-cloudsql-instances`. Redeploy with the flag — the socket only exists inside the container when Cloud Run mounts it.

### `password authentication failed for user "video_agent"`

`DB_PASS` in `cloud-run-env.yaml` doesn't match the password set in Step 3b. Re-run the `gcloud sql users` command to reset it:

```bash
gcloud sql users set-password video_agent \
  --instance=video-agent-sessions \
  --password=NEW_PASSWORD \
  --project=ai-tutor-dev-videos
```

Then update `cloud-run-env.yaml` and redeploy.

### `FATAL: database "video_agent_sessions" does not exist`

The database wasn't created in Step 3a, or the `DB_NAME` env var has a typo. Verify:

```bash
gcloud sql databases list --instance=video-agent-sessions --project=ai-tutor-dev-videos
```

### Sessions still use SQLite after deploy

`CLOUDSQL_INSTANCE` wasn't picked up. Check:

1. The variable is present in `cloud-run-env.yaml` with no typos
2. You deployed **after** updating the file (env vars are baked in at deploy time)
3. Run the following to confirm the env var is set on the live revision:

```bash
gcloud run services describe video-agent \
  --region us-central1 \
  --format="yaml(spec.template.spec.containers[0].env)"
```

### `roles/cloudsql.client` already granted but still getting permission errors

Make sure the service account identity matches exactly. The Cloud Run service must be running as `video-agent@ai-tutor-dev-videos.iam.gserviceaccount.com`. Verify:

```bash
gcloud run services describe video-agent \
  --region us-central1 \
  --format="value(spec.template.spec.serviceAccountName)"
```

---

## Notes on ADK schema migrations

ADK Python v1.22.0 changed the session database schema. If you ever upgrade `google-adk` across that boundary on an existing database, you'll need to run the migration described in the [ADK session migration docs](https://adk.dev/sessions/session/migrate/). Since this setup starts with a fresh database, no migration is needed initially.

For this reason the instructions in `sql-session-plan.md` recommend a dedicated database (not shared with other app tables). This setup follows that: `video_agent_sessions` is ADK-only.
