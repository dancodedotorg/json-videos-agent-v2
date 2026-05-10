# json-video-player

A browser-based "fake video player" that plays structured JSON files instead of real video. Each JSON file describes a sequence of scenes, where each scene is a self-contained HTML document rendered in an iframe. Designed to be LLM-friendly: simple enough for an AI to generate, human-editable, and exportable to MP4 via FFmpeg.js. 

## Project Structure

The project has two distinct parts:

### Player (root)
The core video player — do not modify unless working on player features.

- `json-video.js` — `<json-video>` custom web component (playback, captions, audio sync)
- `json-video-styles.js` — player CSS
- `video-exporter.js` — FFmpeg.js-based MP4 export
- `index.html` — editor/player UI (load JSON, edit scenes, preview, export)
- `examples/example.json` — reference example of the JSON video format

### Generation (`generation/`)
Everything needed to author and generate video content. This is the active working area.

```
generation/
├── tools/
│   ├── paths.py                     ← shared lib: canonical path helpers for the unit→lesson→video hierarchy
│   ├── text_utils.py                ← shared lib: normalize_text() / normalize_data() strip curly quotes/fancy dashes to ASCII
│   ├── script_review.py             ← standalone utility (not called by any skill)
│   ├── .env                         ← API credentials (ELEVENLABS_API_KEY, GOOGLE_API_KEY, etc.)
│   └── generated-images/            ← output directory for gemini-image-gen.py
├── units/                           ← curriculum units (new-style video organization)
│   ├── <unit-slug>/
│   │   ├── unit.json                ← lesson list with resources, vocabulary, objectives per lesson
│   │   └── lessons/
│   │       └── <lesson-slug>/
│   │           ├── sources.csv      ← lesson-level: slides, doc, level_summary, ALL vocab, ALL objectives
│   │           ├── lesson-state.json← tracks grounding status (written by /lesson-ground)
│   │           ├── source/          ← fetched once, shared by all videos in this lesson
│   │           └── videos/
│   │               └── <video-name>/
│   │                   ├── audio/
│   │                   ├── images/
│   │                   ├── scenes/
│   │                   └── script.json  ← includes unit, lesson, target_objectives metadata
│   └── standalone/                  ← pseudo-unit for lessons not in a curriculum unit
│       └── lessons/
```

### Generation workflow (new-style)

```
/unit-init  <unit-slug>                    → one-time: creates unit.json from Code.org API
/lesson-init <unit> <lesson>               → one-time per lesson: creates lesson folder, auto-populates sources.csv
/lesson-ground <unit> <lesson>             → fetches lesson source materials (can re-run to refresh)
/lesson-plan  <unit> <lesson>               → preferred: analyzes objectives, recommends video split, initializes ALL videos
/video-init  <unit> <lesson> <video>       → add a single video outside an existing plan
                                             do NOT call after /lesson-plan — videos are already initialized
/video-create <unit> <lesson> <video>      → orchestrates script → html → audio → assemble
```

Each video's `script.json` stores `unit`, `lesson`, and `target_objectives` so all skills can resolve paths deterministically. The lesson `source/` folder is shared across all videos in that lesson — grounding happens once at the lesson level, not per-video.

## JSON Video Format

Each video's `script.json` includes `unit`, `lesson`, and `target_objectives`:

```json
{
  "video_name": "objective-1",
  "unit": "problem-solving-with-ai",
  "lesson": "lesson-2-beyond-words",
  "target_objectives": [
    "Experiment with different media inputs to observe AI's interpretation and limitations.",
    "Explain that multimodal AI models process information from multiple types of input."
  ],
  "target_vocabulary": [
    "multimodal model"
  ],
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

`pipeline.grounding` is pre-set to `"complete"` at video-init time — grounding happens at the lesson level. `target_objectives` acts as the lens for script generation. `target_vocabulary` lists the specific vocab terms this video should define and reinforce — a term may appear in multiple videos if it supports the content of each. Both fields are set by `/lesson-plan` (via `init_videos.py`) or manually by `/video-init`.

The `html` field is the primary authoring target. It must be a complete, self-contained HTML document.

`script.json` exists in two states: **pre-assembly** (per-scene `audio` paths, local `<img>` paths) and **post-assembly** (top-level `"audio"` as base64 URI, images embedded as data URIs). Use `base64_clean.py` before reading a post-assembled script.

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

## Slide Design System

All slides follow a fixed-canvas approach: designed at **1600×900px**, scaled to fit the player via CSS viewport units. This means:

- **All sizing in `rem`** — the `:root` sets `font-size: calc(16vh / 9)`, making `1rem = 16px` at the design height of 900px. All dimensions scale proportionally as the viewport resizes. Do not use bare `px` for layout values.
- **All colors via CSS custom properties** — `var(--color-teal)`, `var(--color-purple)`, etc. No hardcoded hex values in slide-specific styles
- **No external dependencies** except Google Fonts (Barlow Semi Condensed + Figtree)
- **Every slide includes the same boilerplate** `<style>` block — never modify it. There is no resize script.

See `.agents/skills/video-html/references/design-guide.md` for the full color palette, typography scale, and layout principles.

## Generating Slides

**Full guidance is in `.agents/skills/video-html/references/`.** Two key files:

- `template-selection.md` — visual approach overview (text vs. image gen vs. SVG) and template catalog; used during planning
- `generation-guide.md` — connected sequences, slide text density, HTML requirements, animation guidelines; used during generation

Key points:

- There are three visual approaches: text-based HTML templates, AI image generation, and inline SVG
- Always read the full script before assessing individual scenes — connected sequences must be identified and planned as a group before any generation begins
- Use the `/video-html` skill (`.agents/skills/video-html/`) as the task specification when starting a new slide generation session

## Tools

### Shared libraries (`generation/tools/`)

`paths.py` and `text_utils.py` remain in `generation/tools/` as shared Python libraries — they are not runnable scripts, just modules imported by skill scripts. Skill scripts reference them via `sys.path.insert(0, str(Path.cwd() / "generation" / "tools"))`.

### `generation/tools/text_utils.py`
Shared text sanitization. Two functions:
- `normalize_text(text)` — replaces curly quotes, smart apostrophes, en/em dashes, and ellipsis with ASCII equivalents
- `normalize_data(obj)` — recursively applies `normalize_text` to all string values in any dict or list

Import this in any script that reads data from an external source (Code.org API, Google, LLM output) before saving to a file or calling an external API.

### `generation/tools/paths.py`
Canonical path helper module. Provides functions like `unit_root()`, `lesson_root()`, `video_root()`, `video_script()` etc.

## Shell Commands

Always use `python` (not `python3`) when running scripts from the shell.

**Skill script paths:** Script paths inside skill instructions (e.g., `scripts/foo.py`) are relative to the skill's own directory, not the project root. When running commands from a skill, expand them to their full project-relative form: `.agents/skills/<skill-name>/scripts/foo.py`. For example, `python scripts/fetch_unit.py` in the `unit-init` skill becomes `python .agents/skills/unit-init/scripts/fetch_unit.py`.

## Player Development

```bash
npx http-server . --cors -p 4173 \
  --header "Cross-Origin-Opener-Policy: same-origin" \
  --header "Cross-Origin-Embedder-Policy: require-corp"
```

SharedArrayBuffer (required for FFmpeg export) needs the COOP/COEP headers above. VS Code Live Preview also works for basic playback without export.

Tests: `npx playwright test`
