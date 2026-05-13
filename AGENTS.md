# video-generation-agent

Educational video generation agent for Code.org. Produces structured JSON videos — each a `script.json` containing self-contained HTML slide documents and MP3 audio — via a multi-stage AI pipeline built on Google ADK.

## Project Structure

The project has two main working areas:

### Backend (`backend/`)
The ADK agent, all skills, and the custom Python tools.

- `backend/agent.py` — root ADK agent definition (model, skills, tools, instructions)
- `backend/skills/` — 11 modular skills following the agentskills.io spec
- `backend/tools/` — 3 custom Python tools registered directly with the agent
- `backend/requirements.txt` — dependencies for Cloud Run and local ADK sessions

### Generation (`generation/`)
Curriculum data and shared script libraries.

```
generation/
├── tools/
│   ├── paths.py                     ← shared lib: canonical path helpers for the unit→lesson→video hierarchy
│   ├── text_utils.py                ← shared lib: normalize_text() / normalize_data() strip curly quotes/fancy dashes to ASCII
│   ├── script_tool.py               ← shared lib: get/set/view accessor for individual script.json fields
│   ├── script_review.py             ← standalone utility (not called by any skill)
│   ├── .env                         ← API credentials (ELEVENLABS_API_KEY, GOOGLE_API_KEY, etc.)
│   └── requirements.txt             ← local dev dependencies for skill scripts
├── units/                           ← curriculum units (created as you initialize them)
│   ├── <unit-slug>/
│   │   ├── unit.json                ← lesson list with resources, vocabulary, objectives per lesson
│   │   ├── lessons.json             ← raw lesson list from Code.org API
│   │   ├── resources.json           ← raw resource data from Code.org API
│   │   └── lessons/
│   │       └── <lesson-slug>/
│   │           ├── sources.csv      ← lesson-level: slides, doc, level_summary, ALL vocab, ALL objectives
│   │           ├── lesson-state.json← tracks grounding status (written by /lesson-ground)
│   │           ├── lesson-plan.json ← approved video plan with modes and objectives (written by /lesson-plan)
│   │           ├── source/          ← fetched once, shared by all videos in this lesson
│   │           └── videos/
│   │               └── <video-name>/
│   │                   ├── script.json          ← pipeline state + scenes
│   │                   ├── script_cleaned.json  ← base64-stripped copy (temp, created by video-html)
│   │                   ├── scenes_draft.json    ← draft scenes array (temp, created by video-script)
│   │                   ├── audio/
│   │                   ├── images/
│   │                   ├── scenes/
│   │                   ├── script_assembled_base64.json ← final player-ready file
│   │                   └── video_archive.zip    ← source archive for re-editing
│   └── standalone/                  ← pseudo-unit for lessons not in a curriculum unit
│       └── lessons/
```

### Entry point and deployment
- `main.py` — FastAPI entry point used by both `adk web` and Cloud Run. Detects `CLOUDSQL_INSTANCE` and `ARTIFACT_BUCKET` env vars at startup: if set, sessions go to Cloud SQL (PostgreSQL) and artifacts to GCS; otherwise falls back to SQLite + in-memory (local dev only).
- `Dockerfile` — bakes `generation/units/` data snapshot and `backend/` into the image at build time

See `GCS_SETUP_INSTRUCTIONS.md` and `SQL_SETUP_INSTRUCTIONS.md` for one-time Cloud Run infrastructure setup.

---

## Generation Workflow

```
/unit-init  <unit-slug>                    → one-time: creates unit.json from Code.org API
/lesson-init <unit> <lesson>               → one-time per lesson: creates lesson folder, auto-populates sources.csv
/lesson-ground <unit> <lesson>             → fetches lesson source materials (can re-run to refresh)
/lesson-plan  <unit> <lesson>              → preferred: asks for video type(s), analyzes objectives (for re-teach), recommends split, initializes ALL videos
/video-init  <unit> <lesson> <video>       → add a single video outside an existing plan
                                             do NOT call after /lesson-plan — videos are already initialized
/video-create <unit> <lesson> <video>      → orchestrates script → html → audio → assemble
```

Each video's `script.json` stores `unit`, `lesson`, and `target_objectives` so all skills can resolve paths deterministically. The lesson `source/` folder is shared across all videos in that lesson — grounding happens once at the lesson level, not per-video.

### Skill context split

The 11 skills are split across two running contexts:

**Claude Code only** (use Skill tool locally; these are NOT registered in the ADK web agent):
- `unit-init`, `lesson-init`, `lesson-ground`, `lesson-plan`

**ADK web + Claude Code** (registered in `backend/agent.py` and available in both contexts):
- `video-init`, `video-script`, `video-html`, `video-audio-tags`, `video-audio`, `video-assemble`, `video-create`

When running `adk web backend/` or the deployed Cloud Run service, lesson grounding is handled by the `ground_lesson` Python tool rather than the `lesson-ground` skill.

---

## JSON Video Format

Each video's `script.json` includes `unit`, `lesson`, and `target_objectives`:

```json
{
  "video_name": "objective-1",
  "unit": "problem-solving-with-ai",
  "lesson": "lesson-2-core-concepts",
  "target_objectives": [
    "Experiment with different media inputs to observe AI's interpretation and limitations.",
    "Explain that multimodal AI models process information from multiple types of input."
  ],
  "target_vocabulary": [
    "multimodal model"
  ],
  "mode": "concept",
  "brief": null,
  "width": 1600,
  "height": 900,
  "pipeline": {
    "grounding": "complete",
    "script": "complete",
    "html": "complete",
    "audio_tags": "complete",
    "audio": "complete",
    "assembled": false
  },
  "tts": {},
  "scenes": [
    {
      "comment": "Scene description",
      "duration": "8.5s",
      "html": "<complete self-contained HTML document>",
      "speech": "Caption text shown to viewer",
      "elevenlabs": "[tone] narration text for ElevenLabs",
      "gemini": "[tone] narration text for Gemini TTS",
      "audio": "audio/scene_01.mp3"
    }
  ]
}
```

`pipeline.grounding` is pre-set to `"complete"` at video-init time — grounding happens at the lesson level. `target_objectives` acts as the lens for script generation. `target_vocabulary` lists the specific vocab terms this video should define and reinforce. `mode` is one of `concept`, `summary`, `re-teach`, or `co-create` — set at plan/init time, read by `video-script` to select the appropriate style guide. `brief` is `null` for predefined modes (the style guide is the brief) or a custom string for `co-create` (audience, angle, tone, length). All of these fields are set by `/lesson-plan` (via `init_videos.py`) or manually by `/video-init`.

The `html` field is the primary authoring target. It must be a complete, self-contained HTML document. **HTML is not stored in `script.json` during the pipeline** — `video-html` writes slides to `scenes/scene_NN.html` on disk, and `video-assemble` reads them from there at assembly time. This keeps `script.json` small (3–10 KB) throughout the pipeline until final assembly.

`script.json` exists in two states: **pre-assembly** (per-scene `audio` paths, `scenes[].html` is empty, HTML lives in `scenes/`) and **post-assembly** (`script_assembled_base64.json` — all assets embedded as base64 URIs, written to a separate file). Never read `script_assembled_base64.json` into context — it is too large and is saved as a downloadable artifact.

To read or write individual fields in `script.json` without loading the entire file, use `script_tool.py` (see Tools section below).

---

## Text Conventions

**Always use ASCII-safe punctuation in any text you generate** — narration, captions, vocabulary definitions, objectives, slide copy, comments, everything. This applies across all file types.

| Instead of | Use |
|---|---|
| `'` `'` (curly apostrophe / single quotes) | `'` |
| `"` `"` (curly double quotes) | `"` |
| `–` (en dash) | `-` |
| `—` (em dash) | ` - ` |
| `…` (ellipsis character) | `...` |

Unicode typography characters cause silent failures in TTS pipelines and other downstream tools. `generation/tools/text_utils.py` provides `normalize_text()` (single string) and `normalize_data()` (recursively walks any dict/list) as a safety net — applied at every external data ingestion point (`filter_resources.py`, `google-fetch.py`, `init_lesson.py`) and before every TTS API call. The source text should still be clean before it gets there.

---

## Slide Design System

All slides follow a fixed-canvas approach: designed at **1600×900px**, scaled to fit the player via CSS viewport units. This means:

- **All sizing in `rem`** — the `:root` sets `font-size: calc(16vh / 9)`, making `1rem = 16px` at the design height of 900px. All dimensions scale proportionally as the viewport resizes. Do not use bare `px` for layout values.
- **All colors via CSS custom properties** — `var(--color-teal)`, `var(--color-purple)`, etc. No hardcoded hex values in slide-specific styles
- **No external dependencies** except Google Fonts (Barlow Semi Condensed + Figtree)
- **Every slide includes the same boilerplate** `<style>` block — never modify it. There is no resize script.

See `backend/skills/video-html/references/design-guide.md` for the full color palette, typography scale, and layout principles.

---

## Generating Slides

**Full guidance is in `backend/skills/video-html/references/`.** Two key files:

- `template-selection.md` — visual approach overview (text vs. image gen vs. SVG) and template catalog; used during planning
- `generation-guide.md` — connected sequences, slide text density, HTML requirements, animation guidelines; used during generation

Key points:

- There are three visual approaches: text-based HTML templates, AI image generation, and inline SVG
- Always read the full script before assessing individual scenes — connected sequences must be identified and planned as a group before any generation begins
- Use the `/video-html` skill (`backend/skills/video-html/`) as the task specification when starting a new slide generation session

---

## Tools

### Shared libraries (`generation/tools/`)

`paths.py`, `text_utils.py`, and `script_tool.py` are shared Python libraries in `generation/tools/` — not runnable scripts, just modules imported by skill scripts. Skill scripts reference them via `sys.path.insert(0, str(Path.cwd() / "generation" / "tools"))`.

### `generation/tools/text_utils.py`
Shared text sanitization. Two functions:
- `normalize_text(text)` — replaces curly quotes, smart apostrophes, en/em dashes, and ellipsis with ASCII equivalents
- `normalize_data(obj)` — recursively applies `normalize_text` to all string values in any dict or list

Import this in any script that reads data from an external source (Code.org API, Google, LLM output) before saving to a file or calling an external API.

### `generation/tools/paths.py`
Canonical path helper module. Provides functions like `unit_root()`, `lesson_root()`, `video_root()`, `video_script()` etc.

### `generation/tools/script_tool.py`
Accessor utility for reading and writing individual fields in `script.json` without loading the entire file. Use this instead of reading/writing the whole JSON when you only need one value.

```bash
# Read a single field (dot-notation path, supports list indices)
python generation/tools/script_tool.py get script.json pipeline.script
python generation/tools/script_tool.py get script.json scenes.2.speech

# Write a single scalar value (atomic temp+rename write)
python generation/tools/script_tool.py set script.json pipeline.audio complete
python generation/tools/script_tool.py set script.json tts.provider gemini

# Pretty-print with large scene fields omitted (drops ~50 KB to ~6 KB)
python generation/tools/script_tool.py view script.json
python generation/tools/script_tool.py view script.json --omit html,elevenlabs,gemini
```

All writes use an atomic temp-file + rename pattern — `script.json` is never left in a partially-written state.

### ADK backend tools (`backend/tools/`)

These tools are registered with the ADK agent (`backend/agent.py`) and are available during `adk web` sessions only — not in Claude Code skill runs.

**`ground_lesson(unit, lesson)`** — two-phase grounding tool. First call: resolves the lesson slug and generates `sources.csv` from Code.org curriculum data, returning `status: sources_csv_generated` for agent review. Second call (after `sources.csv` is confirmed on disk): runs `ground-lesson.py` to fetch all source materials. Returns `{status, lesson_slug, sources_fetched, errors}`. Status values: `already_complete`, `sources_csv_generated`, `needs_sources_csv` (standalone), `complete`, `partial`, `error`.

**`load_lesson_sources(unit, lesson)`** — saves lesson source files from `generation/units/<unit>/lessons/<lesson>/source/` as ADK session artifacts. Idempotent: if artifacts with the `<lesson>__` prefix already exist in the session, returns `status: already_loaded` immediately. Supported types: PDFs (as `application/pdf`), JSON (base64 payloads stripped before save), Markdown. Returns `{status, artifacts, errors}`.

**`load_artifacts`** (provided by `LoadArtifactsTool`) — retrieves saved artifacts into the model's context for one turn. PDFs are injected as native multimodal parts that Gemini can read in full; JSON arrives pre-cleaned. Artifact content is **not stored in session history** — it is only present for the turn in which `load_artifacts` is called. Call it again in any later turn that needs the same source materials.

**`save_video_output(unit, lesson, video)`** — called after `video-assemble` completes. Saves `script_assembled_base64.json` and `video_archive.zip` as downloadable session artifacts. Do NOT read these files into context — save them as artifacts and instruct the user to download from the artifacts panel.

Artifact names use `<lesson-slug>__<filename>` (double underscore). Key source artifact names:
- `<lesson>__slides_notes.pdf` — slide images + speaker notes
- `<lesson>__slides_data.json` — structured slide data
- `<lesson>__lesson_levels.json` — lesson level data
- `<lesson>__objectives.md`, `<lesson>__vocabulary.md`

---

## Shell Commands

**Skill script paths:** Script paths inside skill instructions (e.g., `scripts/foo.py`) are relative to the skill's own directory, not the project root. When running commands from a skill, expand them to their full project-relative form: `backend/skills/<skill-name>/scripts/foo.py`. For example, `python scripts/fetch_unit.py` in the `unit-init` skill becomes `python backend/skills/unit-init/scripts/fetch_unit.py`.
