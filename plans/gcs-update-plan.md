Now I have everything I need. Let me write the proposal.Here's a thorough breakdown of the diagnosis and your options.

---

## Root cause diagnosis

The "failed to fetch artifact" error on Cloud Run but not locally is a classic **stateless ephemeral storage problem**, compounded by a confirmed ADK regression bug. There are actually two distinct failure modes at play:

**Failure mode 1 — Multi-instance request routing.** Cloud Run can run many container replicas simultaneously, and it routes each HTTP request to any available instance with no guarantee of session affinity. When your agent saves an artifact during a run, it's written into the in-process memory of instance A. The browser then makes a separate `GET /apps/.../artifacts/{name}` request that may land on instance B — which has no memory of that artifact — resulting in a 404 or "failed to fetch."

**Failure mode 2 — Confirmed ADK regression (Issue #2503).** Even if you passed `--artifact_service_uri='gs://my-bucket'` to `adk deploy cloud_run`, there's a documented regression introduced between ADK 1.8 and 1.10 where the Cloud Run deployment ignores that flag and silently falls back to `InMemoryArtifactService`. Cloud Run logs will say "Using InMemoryArtifactService" even when you expected GCS. This bug is tagged `wip` (in-progress fix) on GitHub as of 2025.

This also explains the local/cloud discrepancy perfectly: locally you have one process, one instance, one memory space — everything works fine. In Cloud Run you have multiple stateless instances, so cross-instance fetches fail unpredictably.---

## Three viable options compared

### Option 1 — Switch to `GcsArtifactService` (fix the ADK artifact system properly)

**What to do.** Because the `--artifact_service_uri` CLI flag is broken on Cloud Run, you have to wire GCS up manually via a `server.py` that calls `get_fast_api_app()` directly:

```python
# server.py
import os
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.artifacts import GcsArtifactService

app = get_fast_api_app(
    agents_dir=os.path.dirname(__file__),
    web=True,
    artifact_service_uri=f"gs://{os.environ['ARTIFACT_BUCKET']}",
    # OR use artifact_service_instance= if you want more control
)
```

Then deploy with `gcloud run deploy` pointing to this `server.py` entry point instead of using `adk deploy cloud_run`.

**Why this works.** `GcsArtifactService` stores every artifact as a blob at the path `{app_name}/{user_id}/{session_id}/{filename}/{version}` in your bucket. All instances share the same bucket, so it doesn't matter which instance handles the fetch request.

**Caveats and known bugs to watch for:**
- The `GcsArtifactService` hard-codes path parsing that expects blob names in a strict 5-element format, which breaks when you use it alongside the Vertex AI session service. This causes crashes in `list_artifact_keys` due to tuple unpacking. If you're using `VertexAISessionService`, apply the workaround from Issue #1436 or use `InMemorySessionService` + `GcsArtifactService` for now.
- Artifacts saved to GCS may not appear in the ADK web UI sidebar when the save is preceded by an auth flow, due to a disconnect in SSE event propagation or state management. The files land in GCS successfully but the UI doesn't reflect the update.
- Starting with ADK v1.2.0, the web UI relies on the `mime_type` of an artifact to render it correctly. Saving an artifact without setting `mime_type` (e.g. `'image/png'`, `'application/pdf'`) causes broken image/download links in the sidebar.

**Tradeoffs:**

| | |
|---|---|
| ✅ One-line switch from InMemory | The `GcsArtifactService` is a drop-in, modulo bugs |
| ✅ Artifacts survive container restarts | Persistent, survives scale-to-zero |
| ✅ Stays within the ADK artifact paradigm | No UI refactoring needed |
| ⚠️ Active known bugs in the GCS path | The session-service path-parsing bug and sidebar refresh bug are real |
| ⚠️ ADK bug #2503 means you can't use the CLI flag | Must write custom `server.py` entry point |
| ⚠️ GCS bucket IAM to configure | Cloud Run service account needs `roles/storage.objectAdmin` on the bucket |

**Recommendation if choosing this path:** pin to a specific ADK version where GCS worked (pre-1.10 or wait for the #2503 fix to land), use `InMemorySessionService` to avoid the path-parsing crash, and always set `mime_type` on saved artifacts.

---

### Option 2 — Bypass ADK artifacts: upload to GCS directly, return a signed URL

**What to do.** Inside your tool, instead of `tool_context.save_artifact(...)`, upload the file directly to GCS using the `google-cloud-storage` library and generate a signed URL (or a plain public URL). Return the URL as text in the agent's response so the user can click it.

```python
from google.cloud import storage
import datetime

def generate_and_deliver_file(tool_context, content: bytes, filename: str) -> str:
    client = storage.Client()
    bucket = client.bucket(os.environ["ARTIFACT_BUCKET"])
    blob = bucket.blob(f"downloads/{filename}")
    blob.upload_from_string(content, content_type="application/pdf")

    url = blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(hours=24),
        method="GET",
    )
    return f"Your file is ready: [Download {filename}]({url})"
```

**Why this avoids the problem entirely.** There's no in-process state involved at all. The file lives in GCS, the URL is a self-contained signed token, and the browser downloads directly from GCS — the ADK web UI's artifact fetch endpoint is never involved.

**Tradeoffs:**

| | |
|---|---|
| ✅ Completely bypasses all ADK artifact bugs | No dependency on `GcsArtifactService` or the fetch endpoint |
| ✅ Links work from any browser, shareable | The signed URL is bearer-token-based |
| ✅ Download directly from GCS | No round-trip through your Cloud Run service |
| ⚠️ Abandons the ADK artifact sidebar | Files won't appear in the web UI's artifact panel |
| ⚠️ Signed URLs require a service account key for signing | Workload identity federation works but requires setup; alternatively use uniform bucket-level access with short-lived tokens |
| ⚠️ No versioning or session scoping | You'd need to implement your own path scheme if you want session-scoped access |
| ⚠️ URLs expire | 24h is typical; user must download before expiry |

**Recommendation if choosing this path:** use `blob.generate_signed_url()` with a 24–48h expiry, and namespace the GCS path by session ID (`downloads/{session_id}/{filename}`) to keep things organized. For service account signing, grant `roles/iam.serviceAccountTokenCreator` to the Cloud Run service account on itself.

---

### Option 3 — Custom download route in your FastAPI app

**What to do.** Keep using `GcsArtifactService` for storage, but add a custom FastAPI route that serves the file content directly from GCS, bypassing the ADK web UI's fetch endpoint. Have your agent emit a URL to this route in the chat response.

```python
from fastapi import Response
from google.cloud import storage

@app.get("/download/{session_id}/{filename}")
async def download_artifact(session_id: str, filename: str):
    client = storage.Client()
    blob = client.bucket(os.environ["ARTIFACT_BUCKET"]).blob(
        f"my_app/user/{session_id}/{filename}/0"
    )
    data = blob.download_as_bytes()
    return Response(content=data, media_type="application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})
```

**Tradeoffs:**

| | |
|---|---|
| ✅ Full control over auth, headers, expiry logic | You own the endpoint behavior |
| ✅ Can add access control (verify user/session) | ADK's built-in endpoint has no auth |
| ✅ URLs are stable (no expiry unless you add it) | |
| ⚠️ More boilerplate | You're implementing what GcsArtifactService + the fetch endpoint should give you |
| ⚠️ Still needs GCS bucket configured | Same IAM requirements as Option 1 |
| ⚠️ Download traffic routes through Cloud Run | Counts against Cloud Run egress costs and instance memory |

---

## Recommendation

The right path depends on how much you want to stay inside the ADK paradigm:

**If you want the cleanest fix with minimum refactoring:** go with **Option 1**, but do it properly — bypass the broken CLI flag and wire `GcsArtifactService` via a custom `server.py`. Check your ADK version against the bug tracker and pin to a version where GCS is stable. Be prepared to work around the sidebar refresh bug (it's cosmetic — the file is there, the panel just doesn't update).

**If your primary goal is reliable user downloads and you don't care about the artifact sidebar:** go with **Option 2**. It's the most robust — no ADK artifact plumbing at all, a signed URL in the chat message is actually a better UX for download intent than a sidebar panel anyway, and it removes the entire dependency on buggy ADK service code.

**If you need access control on downloads and want URLs that don't expire:** go with **Option 3**.

The combination I'd suggest for most cases is **Option 1 for in-conversation artifact context** (so the agent can reference its own prior outputs) **+ Option 2 for user-facing download links** — store in GCS via `GcsArtifactService`, and also emit a signed URL in the agent's text response so the download path is entirely reliable regardless of which Cloud Run instance handles the request.



# GCS Bucket Settings

Here's a practical reference covering every bucket setting that matters for this use case.

---

## Bucket creation

**Location:** Put the bucket in the same region as your Cloud Run service (e.g. `us-central1`). Cross-region calls add latency and egress cost to every artifact read and write.

**Storage class:** `Standard`. Artifacts are accessed frequently during a session — Nearline/Coldline/Archive impose minimum storage durations and retrieval fees that make no sense for session data.

**Public access prevention:** Leave `Enforce public access prevention` **on** (the default). The bucket should never be public. All access flows through your Cloud Run service account.

---

## Access control

Use **uniform bucket-level access** (Google's recommended setting). This means IAM alone manages permissions — no legacy ACLs — and you get access to features like managed folders and IAM Conditions that fine-grained access doesn't support. Once you enable it, don't disable it.

**The IAM binding that matters most** is on your Cloud Run service account. `GcsArtifactService` needs to read, write, list, and delete blobs, so grant it `roles/storage.objectAdmin` **scoped to just this bucket**, not project-wide:

```bash
# Get your Cloud Run service account
SA="$(gcloud run services describe YOUR_SERVICE \
  --region=YOUR_REGION \
  --format='value(spec.template.spec.serviceAccountName)')"

# Grant objectAdmin on the bucket only
gcloud storage buckets add-iam-policy-binding gs://YOUR_BUCKET \
  --member="serviceAccount:${SA}" \
  --role="roles/storage.objectAdmin"
```

If you don't have a dedicated service account yet (Cloud Run defaults to the Compute Engine default SA, which is overprivileged for everything else), it's worth creating one:

```bash
gcloud iam service-accounts create adk-agent-sa \
  --display-name="ADK Agent Service Account"

gcloud run services update YOUR_SERVICE \
  --service-account=adk-agent-sa@YOUR_PROJECT.iam.gserviceaccount.com \
  --region=YOUR_REGION
```

**If you're generating signed URLs** (Option 2 from the earlier proposal), the service account also needs permission to sign blobs on itself:

```bash
gcloud iam service-accounts add-iam-policy-binding \
  adk-agent-sa@YOUR_PROJECT.iam.gserviceaccount.com \
  --member="serviceAccount:adk-agent-sa@YOUR_PROJECT.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountTokenCreator"
```

Without this, `blob.generate_signed_url()` will fail with a credentials error on Cloud Run (it works locally because your personal account has signing rights, but the Cloud Run metadata service identity doesn't by default).

---

## Lifecycle rules

ADK does not garbage-collect old artifact versions automatically, so without a lifecycle rule your bucket accumulates blobs forever. The GCS path structure is `{app_name}/{user_id}/{session_id}/{filename}/{version}`, so you can't easily target just old versions — the practical approach is to delete objects older than N days:

```bash
gcloud storage buckets update gs://YOUR_BUCKET \
  --lifecycle-file=lifecycle.json
```

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

Tune `age` to however long you want artifacts to be fetchable after a session ends. 30 days is a reasonable default; if your users come back weeks later expecting their files, push it higher.

---

## Versioning

Keep GCS **object versioning off**. ADK implements its own versioning by appending a numeric version segment to the blob path (`/0`, `/1`, `/2`...). Enabling GCS-native versioning adds a separate generation layer on top of that, doubling storage consumption with no benefit and making lifecycle rules more complex.

---

## CORS

You only need a CORS configuration if browsers fetch artifacts **directly from GCS** (i.e. you're using signed URLs that point to `storage.googleapis.com`). If all artifact fetches go through your Cloud Run service (the ADK default web UI calls your `/apps/.../artifacts/...` endpoint, not GCS directly), CORS on the bucket is irrelevant and you can skip it.

If you do go the signed URL route:

```json
[
  {
    "origin": ["https://YOUR_CLOUD_RUN_URL"],
    "method": ["GET"],
    "responseHeader": ["Content-Type", "Content-Disposition"],
    "maxAgeSeconds": 3600
  }
]
```

```bash
gcloud storage buckets update gs://YOUR_BUCKET --cors-file=cors.json
```

---

## Quick-reference summary

| Setting | Value | Why |
|---|---|---|
| Location | Same region as Cloud Run | Avoid cross-region latency and egress |
| Storage class | Standard | Frequent access during sessions |
| Access control | Uniform bucket-level | IAM only, simpler, more secure |
| Public access prevention | Enforced (on) | Private bucket |
| IAM binding | `roles/storage.objectAdmin` on service account | Scoped to bucket, not project |
| Signed URL signing | `roles/iam.serviceAccountTokenCreator` on SA | Only if generating signed URLs |
| GCS object versioning | Off | ADK manages its own versioning |
| Lifecycle rule | Delete after 30+ days | ADK doesn't auto-clean old versions |
| CORS | Only if browser hits GCS directly | Not needed for default web UI path |