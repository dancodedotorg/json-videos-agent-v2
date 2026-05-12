# Plan: Prepare Project for Cloud Run Deployment

## Context

The project runs locally via `adk web backend/` but has never been containerized. The goal is to deploy the ADK video generation agent to Google Cloud Run with the ADK web UI included. Key decisions from the Q&A:

- **No Vertex AI** — uses AI Studio `GOOGLE_API_KEY`
- **Ephemeral everything** — filesystem, sessions, and artifacts can all reset on container restart; users save output files themselves
- **Deploy with UI** — `--with_ui` equivalent via `get_fast_api_app(web=True)`
- **Skills must move into `backend/`** — `adk deploy cloud_run` only packages the agent dir; but we're using a custom Dockerfile anyway, so we restructure for correctness
- **`generation/units/` snapshot baked into image** at build time
- **Python 3.12**, concurrency=1, no horizontal scaling, not always-on
- **Credentials**: current production values from `.env` files, passed as Cloud Run env vars
- **Service account key**: keep the base64 JSON approach (not ADC)
- **Request timeout**: 10 minutes (600s)
- **Remove `NEXT_PUBLIC_BACKEND_URL`** — dead code from a previous Next.js iteration

---

## Deployment Architecture

Custom `Dockerfile` at project root + `gcloud run deploy --source .`

We do NOT use `adk deploy cloud_run` because we need to include `generation/units/` and `generation/tools/` in the image alongside `backend/`. A custom Dockerfile gives us full control.

Container layout at `/app`:
```
/app/
  main.py                         ← FastAPI entry point
  backend/
    __init__.py                   ← from . import agent
    agent.py
    requirements.txt
    skills/                       ← moved from .agents/skills/
      video-init/
      video-script/
      ... (all 11 skills)
    tools/
      ground_lesson.py
      load_lesson_sources.py
  generation/
    units/                        ← snapshot baked in at build time
      aif1-v2-2025/
      standalone/
    tools/
      paths.py
      text_utils.py
      script_tool.py              ← included for completeness; agents call it via execute
```

---

## Key Design Decision: Final Output as Artifacts

`video-assemble` writes `script_assembled_base64.json` to the container's ephemeral disk. On Cloud Run, that file vanishes when the session ends. It also contains embedded base64 audio/images (multi-MB) — loading it into the agent's context would exceed token limits.

**Solution**: Add a new `save_video_output` tool that the agent calls as the final step of `video-assemble`. It reads both `script.json` and `script_assembled_base64.json` from disk and saves them as session artifacts via `tool_context.save_artifact`. The ADK web UI displays artifacts the user can download. The files are never injected into the conversation context.

This requires:
- A new tool: `backend/tools/save_video_output.py`
- Registering it in `backend/agent.py`
- Adding a final step to `backend/skills/video-assemble/SKILL.md`
- Adding the tool to the agent instruction

---

## Code Changes

### 1. `backend/__init__.py` — add module import
Currently empty. ADK's agent discovery requires this.
```python
from . import agent
```

### 2. Move `.agents/skills/` → `backend/skills/`
Shell command (do NOT use `cp` — use `git mv` to preserve history):
```bash
git mv .agents/skills backend/skills
```
The `.agents/` directory will then only contain non-skill content (or be empty).

### 3. `backend/agent.py` — update `SKILLS_DIR`
Change line 34:
```python
# Before
SKILLS_DIR = PROJECT_ROOT / ".agents" / "skills"

# After
SKILLS_DIR = pathlib.Path(__file__).parent / "skills"
```
Using `__file__`-relative path is more robust than `PROJECT_ROOT` for container deployments.

Also update the docstring on line 3–4 to reflect the new location.

### 4. `backend/tools/ground_lesson.py` — update script paths
Lines 15–20, change `.agents` → `backend`:
```python
# Before
INIT_LESSON_SCRIPT = (
    PROJECT_ROOT / ".agents" / "skills" / "lesson-init" / "scripts" / "init_lesson.py"
)
GROUND_LESSON_SCRIPT = (
    PROJECT_ROOT / ".agents" / "skills" / "lesson-ground" / "scripts" / "ground-lesson.py"
)

# After — use __file__-relative path into the moved skills dir
_BACKEND_DIR = pathlib.Path(__file__).parent.parent
INIT_LESSON_SCRIPT = _BACKEND_DIR / "skills" / "lesson-init" / "scripts" / "init_lesson.py"
GROUND_LESSON_SCRIPT = _BACKEND_DIR / "skills" / "lesson-ground" / "scripts" / "ground-lesson.py"
```

### 5. `backend/skills/unit-init/scripts/init_all_lessons.py` — update cross-skill reference
One hardcoded `.agents` reference (line ~25):
```python
# Before
init_script = _REPO_ROOT / ".agents" / "skills" / "lesson-init" / "scripts" / "init_lesson.py"

# After
init_script = _REPO_ROOT / "backend" / "skills" / "lesson-init" / "scripts" / "init_lesson.py"
```

### 6. `backend/skills/unit-init/scripts/ground-all.py` — update cross-skill reference
One hardcoded `.agents` reference (line ~25):
```python
# Before
GROUND_LESSON = _REPO_ROOT / ".agents" / "skills" / "lesson-ground" / "scripts" / "ground-lesson.py"

# After
GROUND_LESSON = _REPO_ROOT / "backend" / "skills" / "lesson-ground" / "scripts" / "ground-lesson.py"
```

### 7. `backend/requirements.txt` — add missing packages
The grounding scripts import `googleapiclient` (Google Slides/Docs API). These are not currently listed:
```
google-adk>=1.29.0
python-dotenv
uvicorn           # ← add: server for main.py
fastapi           # ← add: explicit (google-adk brings it, but be explicit)
google-genai
google-api-python-client   # ← add: googleapiclient for Slides/Docs fetch
google-auth-httplib2       # ← add: OAuth transport for service account auth
xhtml2pdf                  # ← add: used by lesson-ground lib scripts (PDF rendering)
elevenlabs
pydub
Pillow
pydantic
```

> **Note on ffmpeg**: Confirmed NOT required. `gemini-audio-gen.py` creates `AudioSegment` from raw PCM bytes and exports to MP3 using pydub's built-in codec — no OS-level ffmpeg needed. `elevenlabs-gen.py` writes MP3 bytes directly without pydub.

### 8. `backend/tools/save_video_output.py` — new tool (save final output as artifacts)

```python
"""Save the final video output files as downloadable session artifacts."""

import pathlib
import google.genai.types as types
from google.adk.tools.tool_context import ToolContext

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent

async def save_video_output(unit: str, lesson: str, video: str, tool_context: ToolContext) -> dict:
    """Save script.json and script_assembled_base64.json as downloadable session artifacts.

    Call this as the final step after video-assemble completes. Saves both files as
    artifacts so the user can download them from the ADK web UI. Neither file is
    loaded into the agent's context — artifacts are stored separately.

    Args:
        unit: Unit slug (e.g. 'aif1-v2-2025')
        lesson: Lesson slug (e.g. 'lesson-2-beyond-words')
        video: Video name (e.g. 'objective-1')

    Returns:
        dict with keys: status, artifacts (mapping filename→artifact_name), errors
    """
    video_root = PROJECT_ROOT / "generation" / "units" / unit / "lessons" / lesson / "videos" / video
    saved = {}
    errors = []

    for filename in ["script.json", "script_assembled_base64.json"]:
        path = video_root / filename
        if not path.exists():
            errors.append(f"{filename} not found — run video-assemble first")
            continue
        artifact_name = f"{unit}__{lesson}__{video}__{filename}"
        part = types.Part.from_bytes(data=path.read_bytes(), mime_type="application/json")
        await tool_context.save_artifact(filename=artifact_name, artifact=part)
        saved[filename] = artifact_name

    return {
        "status": "saved" if not errors else ("partial" if saved else "error"),
        "artifacts": saved,
        "errors": errors,
    }
```

### 8b. `backend/agent.py` — register the new tool

Add import and include `save_video_output` in the tools list:
```python
from backend.tools.save_video_output import save_video_output   # add this import

root_agent = Agent(
    ...
    tools=[skill_toolset, env_toolset, LoadArtifactsTool(), load_lesson_sources, ground_lesson, save_video_output],
)
```

Also add to the agent instruction (in the "Tool usage" section):
```
- save_video_output — call after video-assemble completes with unit, lesson, and video.
  Saves script.json and script_assembled_base64.json as downloadable session artifacts.
  Tell the user to download both files from the artifacts panel before closing the session.
  Do NOT read these files into context — they are too large.
```

### 8c. `backend/skills/video-assemble/SKILL.md` — add final artifact-save step

After the existing "Step 2: Report to user" block, add a new step:

```markdown
### 3. Save output as downloadable artifacts

Call `save_video_output(unit=UNIT, lesson=LESSON_SLUG, video=VIDEO)`.

Then tell the user:

    📦 Your output files are saved as artifacts and are ready to download:
      - script.json — the editable pipeline file
      - script_assembled_base64.json — the player-ready file (load this in the json-video-player)

    ⚠️  These artifacts only exist for this session. Download them before closing.
```

### 9. Remove `NEXT_PUBLIC_BACKEND_URL` from `.env` files
Remove this line from both `.env` (project root) and `generation/tools/.env`:
```
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

---

## New Files

### 9. `main.py` — FastAPI entry point (project root)
```python
import os
import uvicorn
from google.adk.cli.fast_api import get_fast_api_app

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

app = get_fast_api_app(
    agents_dir=AGENT_DIR,
    allow_origins=["*"],
    web=True,
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
```

### 10. `Dockerfile` (project root)
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (layer cache)
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser:appuser /app

# Copy agent package (skills now live inside backend/)
COPY backend/ ./backend/

# Copy generation data snapshot and shared tool libraries
COPY generation/units/ ./generation/units/
COPY generation/tools/paths.py ./generation/tools/paths.py
COPY generation/tools/text_utils.py ./generation/tools/text_utils.py
COPY generation/tools/script_tool.py ./generation/tools/script_tool.py

# Copy FastAPI entry point
COPY main.py .

USER appuser

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
```

### 11. `.dockerignore` (project root)
```
.venv/
.adk/
.agents/
node_modules/
video-json-player/node_modules/
documentation/
plans/
*.pyc
__pycache__/
.env
generation/tools/.env
generation/tools/generated-images/
session.json
*.md
!README.md
```

---

## Path Resolution — Verified Safe

All skill scripts resolve `_REPO_ROOT` via `Path(__file__).resolve().parents[N]`. After moving `.agents/skills/` → `backend/skills/`, the directory depth is identical (`.agents` and `backend` are both one level below project root), so **all `parents[N]` counts remain correct** — no changes needed in the 12 scripts that use this pattern.

In the container, `_REPO_ROOT` resolves to `/app`, and `generation/tools/` is copied there, so `sys.path.insert(0, str(_REPO_ROOT / "generation" / "tools"))` works correctly.

The `load_dotenv(... "generation/tools/.env")` calls in skill scripts are harmless on Cloud Run — the file won't exist in the container, `load_dotenv` silently does nothing, and the env vars set on the Cloud Run service are already in the process environment.

---

## Console Instructions for the User

These are the manual steps to run in the terminal once code changes are done.

### Prerequisites
Make sure you have `gcloud` CLI installed and Docker available locally (Cloud Build handles the build, but you need gcloud authenticated).

### Step 1 — Authenticate and set project
```bash
gcloud auth login
gcloud config set project ai-tutor-dev-videos
```

### Step 2 — Enable required APIs
```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com
```

### Step 3 — Grant Cloud Build permission to the default service account
Cloud Build needs this to push images to Artifact Registry:
```bash
PROJECT_NUMBER=$(gcloud projects describe ai-tutor-dev-videos --format="value(projectNumber)")

gcloud projects add-iam-policy-binding ai-tutor-dev-videos \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/cloudbuild.builds.builder"
```

### Step 4 — Deploy

Pull your three credential values from `generation/tools/.env` and substitute them below. The `GOOGLE_SERVICE_ACCOUNT_JSON` value is the long base64 string.

```bash
gcloud run deploy video-agent \
  --source . \
  --region us-central1 \
  --project ai-tutor-dev-videos \
  --no-allow-unauthenticated \
  --timeout=600 \
  --concurrency=1 \
  --memory=2Gi \
  --set-env-vars="GOOGLE_API_KEY=<your_key>,ELEVENLABS_API_KEY=<your_key>,GOOGLE_SERVICE_ACCOUNT_JSON=<your_base64_json>,GOOGLE_GENAI_USE_VERTEXAI=False"
```

> **Note on IAP**: Since you already have IAP configured, users access the service through your IAP-protected load balancer URL — not the direct Cloud Run service URL. The Cloud Run service is private (`--no-allow-unauthenticated`); IAP handles authentication in front of it. You will need to add this new Cloud Run service as a backend to your existing IAP-protected load balancer (or create a new serverless NEG pointing to `video-agent` in `us-central1` and attach it). The direct Cloud Run URL (`*.run.app`) will return 403 when accessed without an identity token — that is expected.

When prompted:
- `Allow unauthenticated invocations? (y/N)` → press `N` (no public access — IAP handles auth)
- `Create Artifact Registry repository? (y/N)` → press `y`

### Step 5 — Get the service URL and test
```bash
gcloud run services describe video-agent \
  --region us-central1 \
  --format="value(status.url)"
```

Open that URL in a browser. You should see the ADK web UI with the `video_generation_agent` available in the dropdown.

To verify the API is working:
```bash
SERVICE_URL=$(gcloud run services describe video-agent --region us-central1 --format="value(status.url)")
curl -X GET "$SERVICE_URL/list-apps"
```
Expected response: `["backend"]`

### Step 6 — Redeploy after data updates
When you want to bake in a new snapshot of `generation/units/` (e.g., after grounding new lessons locally), simply re-run the deploy command from Step 4. Cloud Build re-builds the image from the current state of the directory.

---

## Critical Files Modified

| File | Change |
|---|---|
| `backend/__init__.py` | Add `from . import agent` |
| `backend/agent.py` | Update `SKILLS_DIR`; register `save_video_output`; update instruction |
| `backend/tools/ground_lesson.py` | Update `INIT_LESSON_SCRIPT` and `GROUND_LESSON_SCRIPT` paths |
| `backend/skills/unit-init/scripts/init_all_lessons.py` | Update `.agents` → `backend` in cross-skill path |
| `backend/skills/unit-init/scripts/ground-all.py` | Update `.agents` → `backend` in cross-skill path |
| `backend/skills/video-assemble/SKILL.md` | Add Step 3: call `save_video_output` and tell user to download |
| `backend/requirements.txt` | Add `uvicorn`, `fastapi`, `google-api-python-client`, `google-auth-httplib2` |
| `.env` + `generation/tools/.env` | Remove `NEXT_PUBLIC_BACKEND_URL` line |

| File | Action |
|---|---|
| `backend/tools/save_video_output.py` | Create — saves final output as session artifacts |
| `main.py` | Create at project root |
| `Dockerfile` | Create at project root |
| `.dockerignore` | Create at project root |
| `.agents/skills/` → `backend/skills/` | `git mv` |

---

## Verification

1. **Local pre-flight**: `docker build -t video-agent-test .` — should complete without errors
2. **Local smoke test**: `docker run -p 8080:8080 -e PORT=8080 -e GOOGLE_API_KEY=... -e ELEVENLABS_API_KEY=... -e GOOGLE_SERVICE_ACCOUNT_JSON=... -e GOOGLE_GENAI_USE_VERTEXAI=False video-agent-test` then open `http://localhost:8080`
3. **API check**: `curl http://localhost:8080/list-apps` → `["backend"]`
4. **Post-deploy**: Open Cloud Run service URL, confirm ADK UI loads, send "hello" to agent, confirm it responds
