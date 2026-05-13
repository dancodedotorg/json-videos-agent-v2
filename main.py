import os
from pathlib import Path

import uvicorn
from fastapi.staticfiles import StaticFiles
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

from backend.preview.preview_routes import router as preview_router

# AG-UI endpoint — bridges the CopilotKit frontend to the ADK agent
from ag_ui_adk import ADKAgent, add_adk_fastapi_endpoint
from backend.agent import root_agent as _root_agent

_ag_ui_agent = ADKAgent(
    adk_agent=_root_agent,
    user_id="copilot_user",
    session_timeout_seconds=3600,
    use_in_memory_services=True,
)
add_adk_fastapi_endpoint(app, _ag_ui_agent, path="/agui")

_player_dir = Path(__file__).parent / "backend" / "static"
if _player_dir.exists():
    app.mount("/player", StaticFiles(directory=str(_player_dir)), name="player")

app.include_router(preview_router)

# Serve the built CopilotKit frontend at /app (present only after `npm run build`)
_app_dir = Path(__file__).parent / "backend" / "static" / "app"
if _app_dir.exists():
    app.mount("/app", StaticFiles(directory=str(_app_dir), html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
