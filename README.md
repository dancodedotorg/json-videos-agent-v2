# Video Generation Agent

An AI agent that generates educational video content for Code.org lessons. Built on Google ADK, deployed to Google Cloud Run.

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
adk web backend/
```

Open `http://localhost:8080` — the ADK web UI will show the `video_generation_agent` in the dropdown.

## Workflow overview

Video generation follows a staged pipeline. Setup steps run once per unit/lesson; the video pipeline runs per video.

| Step | Skill | What it does |
|---|---|---|
| 1 | `/unit-init <unit-slug>` | Fetches lesson list and resources from Code.org API |
| 2 | `/lesson-init <unit> <lesson>` | Creates the lesson folder and `sources.csv` |
| 3 | `/lesson-ground <unit> <lesson>` | Fetches source materials (slides, objectives, vocabulary) |
| 4 | `/lesson-plan <unit> <lesson>` | Analyzes objectives, recommends video split, initializes all video folders |
| 5 | `/video-create <unit> <lesson> <video>` | Runs the full video pipeline: script → HTML slides → audio → assembled JSON |

Steps 1–4 run in Claude Code. Step 5 can run in Claude Code or the ADK web UI.

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
  units/          Curriculum units — populated as you run /unit-init
main.py           FastAPI entry point (adk web + Cloud Run)
Dockerfile        Container definition for Cloud Run deployment
```

## Further reading

- [AGENTS.md](AGENTS.md) — detailed agent reference: JSON format, skill instructions, tool descriptions, text conventions, slide design system
- [ARCHITECTURE.md](ARCHITECTURE.md) — ADK agent structure, skill registry, filesystem layout
- [DEPLOY_INSTRUCTIONS.md](DEPLOY_INSTRUCTIONS.md) — Cloud Run deployment guide
