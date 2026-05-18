# Video Generation Agent

An AI agent that generates educational video content for Code.org lessons. Built on Google ADK, deployed to Google Cloud Run.

This is based on the Claude Skill version of making JSON videos - for a broader overview of the skills and how all this works, [Check out this repo first](https://github.com/dancodedotorg/json-video-generation-claude)

## What this produces

Each "video" is a structured JSON file (`script_assembled_base64.json`) containing:
- A narration script broken into scenes
- Self-contained HTML documents (one per scene, rendered as slides)
- MP3 audio (TTS-generated narration, embedded as base64)

These files load directly into a JSON-based video player. They are not MP4 files.

## Prerequisites

- Python 3.12+ (Python 3.13 requires `backend/requirements-py313.txt` instead)
- API credentials in `generation/tools/.env`:
  ```
  GOOGLE_API_KEY=...
  ELEVENLABS_API_KEY=...
  GOOGLE_SERVICE_ACCOUNT_JSON=...   # base64-encoded service account JSON
  ```
  Copy `generation/tools/.env_example` as a starting point.

## Running locally

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
adk web backend/                   # ADK web UI only
# — or —
uvicorn main:app --reload          # full server: ADK web UI + live preview routes
```

Open `http://localhost:8080` — the ADK web UI will show the `video_generation_agent` in the dropdown.

> Use `uvicorn main:app --reload` instead of `adk web` if you want the live preview (`/preview/<unit>/<lesson>/<video>`) to work during pipeline runs. `adk web` bypasses `main.py` and does not register the preview routes.

## Workflow overview

Video generation follows a staged pipeline. Setup steps run once per unit/lesson; the video pipeline runs per video.

**In the ADK web agent** (the primary workflow):

Tell the agent the unit `/s/` slug and lesson number — it handles grounding, planning, and video generation end-to-end.

| What the agent does | Skill / tool |
|---|---|
| Fetches and grounds lesson source materials | `ground_lesson` tool |
| Analyzes objectives, recommends video split, initializes video folders | `lesson-plan` skill |
| Runs the full video pipeline per video | `video-script` → `video-html` → `video-audio-tags` → `video-audio` → `video-assemble` |

For standalone videos (no Code.org unit), tell the agent the lesson name and provide your own source materials — it skips lesson-plan and goes directly to video generation.

**In Claude Code** (advanced / bulk operations only):

| Step | Skill | What it does |
|---|---|---|
| 1 | `/unit-init <unit-slug>` | Fetches lesson list and resources from Code.org API |
| 2 | `/lesson-init <unit> <lesson>` | Creates the lesson folder and `sources.csv` |
| 3 | `/lesson-ground <unit> <lesson>` | Fetches source materials (slides, objectives, vocabulary) |
| 4 | `/video-create <unit> <lesson> <video>` | Runs the full video pipeline |

The `/video-create` skill orchestrates these sub-stages:

| Sub-stage | What it does |
|---|---|
| `video-init` | Initializes video folder and `script.json` |
| `video-script` | Generates narration scenes using lesson source materials |
| `video-html` | Generates HTML slides (AI image or HTML template approach) |
| `video-audio-tags` | Adds TTS expression tags for ElevenLabs and Gemini |
| `video-audio` | Generates MP3 audio via ElevenLabs or Gemini TTS |
| `video-assemble` | Embeds all assets as base64, produces final JSON |

## Key directories

```
backend/          ADK agent definition, all skills, custom tools
generation/       Curriculum data and shared script libraries
  tools/          Shared Python libs (paths.py, script_tool.py, text_utils.py)
  units/          Curriculum units — created by the agent at runtime, persisted in GCS
main.py           FastAPI entry point (adk web + Cloud Run)
Dockerfile        Container definition for Cloud Run deployment
```

## Further reading

- [AGENTS.md](AGENTS.md) — detailed agent reference: JSON format, skill instructions, tool descriptions, text conventions, slide design system
- [ARCHITECTURE.md](ARCHITECTURE.md) — ADK agent structure, skill registry, filesystem layout
- [DEPLOY_INSTRUCTIONS.md](DEPLOY_INSTRUCTIONS.md) — Cloud Run deployment guide
