Given your stack, the answer is quite clear-cut. You're already using the right artifact backend — `GcsArtifactService` is ADK's built-in implementation for persistent storage using Google Cloud Storage, and you wire it into the `Runner` alongside your session service. The only piece to add is the session service, and for Cloud Run the recommendation is `DatabaseSessionService` + Cloud SQL PostgreSQL.

Here's why that pairing makes sense for your exact setup, and how to configure everything together:

**Why `DatabaseSessionService` over `VertexAiSessionService` for Cloud Run + GCS:**

- Cloud Run is stateless and can scale to multiple instances — you can't guarantee that user requests always hit the same instance, so if request 1 goes to instance A and request 2 goes to instance B, instance B won't have the in-memory session state stored in instance A. Cloud SQL solves this by being a shared external store all instances read from.
- You're already managing GCS infrastructure, so managing a Cloud SQL instance fits naturally in the same operational model. The `VertexAiSessionService` requires provisioning a Reasoning Engine resource which is an entirely different surface.
- In production with `GcsArtifactService`, the ADK web UI's Artifacts sidebar populates correctly because the cloud backend provides the necessary metadata indexing — unlike `InMemoryArtifactService`.

**The complete wiring for your stack:**

```python
from google.adk.sessions import DatabaseSessionService
from google.adk.artifacts import GcsArtifactService
from google.adk.runners import Runner

session_service = DatabaseSessionService(
    db_url="postgresql+asyncpg://user:pass@/dbname"
    #       ^ asyncpg is required — bare postgresql:// won't work
    #         On Cloud Run, use Cloud SQL Auth Proxy socket or direct VPC
)

artifact_service = GcsArtifactService(
    bucket_name="your-existing-gcs-bucket"
)

runner = Runner(
    agent=your_agent,
    app_name="your_app",
    session_service=session_service,
    artifact_service=artifact_service,
)
```

`GcsArtifactService` constructs a hierarchical GCS blob path like `{app}/{user}/{session}/{filename}/{version}`, calculates the next version number automatically based on existing blobs with that prefix, and uploads via the Google Cloud Storage client library. So your existing bucket gets a predictable folder structure with versioning out of the box — no extra configuration needed on the bucket itself.

**IAM you'll need on the Cloud Run service account:**

- `roles/cloudsql.client` — to connect via Cloud SQL Auth Proxy
- `roles/storage.objectAdmin` on your bucket (or just `objectCreator` + `objectViewer` if you want tighter scoping)
- `roles/secretmanager.secretAccessor` if you store your DB credentials in Secret Manager (recommended)

**One thing to watch:** ADK manages the database schema internally, so use a dedicated database (not one shared with your application's other tables) with a separate DB user that has limited access. This protects you from ADK schema migrations on upgrades affecting your own tables. The schema migration requirement was introduced in ADK Python v1.22.0 and can be disruptive if you're sharing a database.

The Cloud SQL Auth Proxy sidecar is the cleanest way to connect on Cloud Run — set your `db_url` host to `127.0.0.1` and let the proxy handle the auth. Google has a specific codelab for exactly this ADK + Cloud SQL + Cloud Run combination if you want a step-by-step reference.