import os

import uvicorn
from google.adk.cli.fast_api import get_fast_api_app

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

_bucket = os.environ.get("ARTIFACT_BUCKET")
_cloudsql_instance = os.environ.get("CLOUDSQL_INSTANCE")
_db_user = os.environ.get("DB_USER", "video_agent")
_db_pass = os.environ.get("DB_PASS", "")
_db_name = os.environ.get("DB_NAME", "video_agent_sessions")

if _cloudsql_instance:
    _session_uri = f"postgresql+asyncpg://{_db_user}:{_db_pass}@/{_db_name}"
    _session_kwargs = {"connect_args": {"host": f"/cloudsql/{_cloudsql_instance}"}}
else:
    _session_uri = "sqlite+aiosqlite:///./sessions.db"
    _session_kwargs = None

app = get_fast_api_app(
    agents_dir=AGENT_DIR,
    session_service_uri=_session_uri,
    session_db_kwargs=_session_kwargs,
    artifact_service_uri=f"gs://{_bucket}" if _bucket else None,
    allow_origins=["*"],
    web=True,
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
