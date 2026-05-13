# Architecture

## ADK Agent Structure

### Agent definition

`backend/agent.py` defines the root agent:

- **Model:** `gemini-3-flash-preview`
- **Name:** `video_generation_agent`
- **Tools:** `SkillToolset` (video pipeline skills), `EnvironmentToolset` (file I/O + shell execution), `LoadArtifactsTool`, plus three custom Python tools
- **Working directory:** project root (via `LocalEnvironment`)
- **Env vars:** loaded from `generation/tools/.env` at startup

### Progressive disclosure

Skills use the agentskills.io progressive disclosure pattern to keep context usage low:

- **L1 (~100 tokens):** Skill name + description. Auto-loaded at startup for all skills. The agent reads this to decide which skill is relevant.
- **L2 (<5,000 tokens):** Full `SKILL.md` instructions. Loaded on demand via `load_skill` when the agent activates a skill.
- **L3 (as needed):** Reference files in `references/` and `assets/`. Loaded via `load_skill_resource` only when the skill instructions call for them.

This means the agent starts each session with roughly 700 tokens of L1 metadata (7 skills × ~100 tokens) rather than the full instruction set for all skills.

---

### Skill registry

11 skills live in `backend/skills/`. They split across two contexts:

| Skill | Registered in agent.py | Running context | Purpose |
|---|---|---|---|
| `unit-init` | No | Claude Code only | Fetch unit lesson list from Code.org API, create `unit.json` |
| `lesson-init` | No | Claude Code only | Create lesson folder and auto-populate `sources.csv` |
| `lesson-ground` | No | Claude Code only | Fetch source materials (slides, levels, objectives, vocab) |
| `lesson-plan` | No | Claude Code only | Analyze objectives, recommend video split, initialize all video folders |
| `video-init` | Yes | ADK web + Claude Code | Initialize video folder and `script.json` |
| `video-script` | Yes | ADK web + Claude Code | Generate narration scenes from source materials |
| `video-html` | Yes | ADK web + Claude Code | Generate HTML slides (template or AI image approach) |
| `video-audio-tags` | Yes | ADK web + Claude Code | Add TTS expression tags for ElevenLabs and Gemini |
| `video-audio` | Yes | ADK web + Claude Code | Generate MP3 audio via ElevenLabs or Gemini TTS |
| `video-assemble` | Yes | ADK web + Claude Code | Embed all assets as base64, produce final JSON |
| `video-create` | Yes | ADK web + Claude Code | Orchestrate the full video pipeline (stages above) |

The 4 lesson/unit setup skills use Claude Code tools (`Read`, `Write`, `Glob`, `Bash`) in their `allowed-tools` frontmatter. They are not loaded into the ADK web agent. In ADK web sessions, lesson setup is handled by the `ground_lesson` custom tool instead.

---

### Custom Python tools

These are registered directly in `backend/agent.py` (not skills) and are available in ADK web sessions only.

**`ground_lesson(unit, lesson)`** — `backend/tools/ground_lesson.py`

Two-phase tool that ensures a lesson's source materials are ready:
- **Phase 1** (no `sources.csv`): resolves the lesson slug, generates `sources.csv` from Code.org curriculum data, returns `status: sources_csv_generated`. The agent shows the source list to the user for review.
- **Phase 2** (`sources.csv` confirmed): runs `ground-lesson.py` to fetch all sources. Returns `status: complete` or `partial`.

Other statuses: `already_complete` (fast path, no action needed), `needs_sources_csv` (standalone lesson with no curriculum data — agent must gather sources from user), `error`.

**`load_lesson_sources(unit, lesson)`** — `backend/tools/load_lesson_sources.py`

Reads the lesson `source/` folder and saves each file as a named ADK session artifact. Idempotent — if artifacts with the `<lesson>__` prefix already exist in the session, returns immediately without re-saving. PDFs saved as `application/pdf` (Gemini reads them natively as multimodal); JSON files have base64 payloads stripped before saving; Markdown saved as `text/plain`.

**`save_video_output(unit, lesson, video)`** — `backend/tools/save_video_output.py`

Called as the final step after `video-assemble`. Saves `script_assembled_base64.json` and `video_archive.zip` as downloadable session artifacts. Neither file is read into context — they are stored as artifacts and the user downloads them from the ADK web UI artifacts panel.

---

### Two running contexts

**Local development — Claude Code**

All 11 skills are available via the `Skill` tool. The 4 lesson setup skills run using Claude Code's native file tools. The 7 video pipeline skills also run via Claude Code, calling Python scripts through `Bash`.

```bash
adk web backend/   # starts the ADK web UI at localhost:8080
```

**Production — Cloud Run**

Only the 7 video pipeline skills are registered. The `ground_lesson` tool handles lesson setup. The `generation/units/` snapshot is baked into the Docker image at build time — source materials must be fetched locally first, then the container rebuilt to include them.

See [DEPLOY_INSTRUCTIONS.md](DEPLOY_INSTRUCTIONS.md) for the full deployment guide.

---

## Filesystem Layout

```
backend/
  agent.py                    ← ADK root agent (model, skills, tools, instructions)
  __init__.py                 ← Package init (imports agent for ADK discovery)
  requirements.txt            ← ADK + script dependencies (Python 3.12)
  requirements-py313.txt      ← Python 3.13+ variant (adds audioop-lts backport)
  skills/
    unit-init/
      SKILL.md                ← L2: instructions + frontmatter (name, description, allowed-tools)
      scripts/
        fetch_unit.py         ← calls Code.org API, writes lessons.json + resources.json
        filter_resources.py   ← produces unit.json from raw API data
        init_all_lessons.py   ← bulk lesson init helper
        ground-all.py         ← bulk grounding helper
      references/
        resources-rollup.user.js ← Tampermonkey script for manual resource export fallback
    lesson-init/
      SKILL.md
      scripts/
        init_lesson.py        ← creates lesson folder, sources.csv from unit.json
    lesson-ground/
      SKILL.md
      scripts/
        ground-lesson.py      ← fetches sources per sources.csv, writes lesson-state.json
        google-fetch.py       ← Google Slides/Docs fetch helper
        lib/                  ← Google API auth, Slides/Docs/Code.org client libs
      references/
        source-types.md       ← documents each sources.csv type and its outputs
    lesson-plan/
      SKILL.md
      scripts/
        init_videos.py        ← reads lesson-plan.json, creates all video script.json files
      references/
        analysis-guide.md     ← objective coupling analysis framework for re-teach planning
    video-init/
      SKILL.md
    video-script/
      SKILL.md
      scripts/
        write-scenes.py       ← merges scenes_draft.json into script.json atomically
        base64_clean.py       ← strips base64 payloads from script.json for safe reading
      references/
        mode-guide.md         ← when to use concept / summary / re-teach / co-create
        concept-style-guide.md
        summary-style-guide.md
        reteach-style-guide.md
        co-create-style-guide.md
    video-html/
      SKILL.md
      scripts/
        gemini-image-gen.py   ← generates images via Gemini, saves to images/
        insert-slides.py      ← inserts HTML slides into script.json (legacy)
        update-pipeline.py    ← updates pipeline.* fields in script.json
        base64_clean.py       ← strips base64 payloads from script.json for safe reading
      assets/                 ← 11 HTML slide templates (title-slide, big-quote, etc.)
      references/
        template-selection.md ← visual approach overview and template catalog
        generation-guide.md   ← HTML requirements, connected sequences, text density
        design-guide.md       ← color palette, typography scale (for template authoring only)
        mode-selection.md     ← Mode C (AI images) vs Mode D (HTML templates) guide
        image-generation.md   ← Visual Director formula and Gemini image prompt assembly
        svg-patterns.md       ← SVG layout conventions and named pattern procedures
        script-editing.md     ← script evaluation rules for scene splits and speech edits
    video-audio-tags/
      SKILL.md
      references/
        elevenlabs-tts-prompting-guide.md
        gemini-tts-prompting-guide.md
    video-audio/
      SKILL.md
      scripts/
        elevenlabs-gen.py     ← generates audio via ElevenLabs, writes scene MP3s
        gemini-audio-gen.py   ← generates audio via Gemini TTS, writes scene MP3s
      references/
        providers.md          ← available providers, voices, and generation modes
    video-assemble/
      SKILL.md
      scripts/
        embed-data.py         ← embeds HTML, audio, images as base64 into script_assembled_base64.json
    video-create/
      SKILL.md               ← orchestrator: runs video-init through video-assemble
  tools/
    ground_lesson.py          ← two-phase lesson grounding tool
    load_lesson_sources.py    ← artifact loader tool
    save_video_output.py      ← output saver tool

generation/
  tools/
    paths.py                  ← canonical path helpers (unit_root, lesson_root, video_root, etc.)
    text_utils.py             ← normalize_text() / normalize_data() — ASCII-safe text
    script_tool.py            ← get/set/view fields in script.json without loading the whole file
    script_review.py          ← standalone review utility (not called by any skill)
    requirements.txt          ← local dev pip dependencies for skill scripts
    .env                      ← API keys: GOOGLE_API_KEY, ELEVENLABS_API_KEY, GOOGLE_SERVICE_ACCOUNT_JSON
    .env_example              ← template showing required keys
  units/                      ← populated as you run /unit-init for each curriculum unit
    <unit-slug>/
      unit.json               ← clean lesson list with per-lesson objectives, vocab, resources
      lessons.json            ← raw lesson list from Code.org API (intermediate)
      resources.json          ← raw resource data from Code.org API (intermediate)
      lessons/
        <lesson-slug>/
          sources.csv         ← source material references (created by lesson-init)
          lesson-state.json   ← grounding status: {grounding, grounded_at, sources_fetched, errors}
          lesson-plan.json    ← approved video plan: {unit, lesson, videos[{name, target_objectives, target_vocabulary, mode, brief}]}
          source/             ← fetched materials, shared by all videos in this lesson
            objectives.md     ← one bullet per learning objective
            vocabulary.md     ← one bullet per vocabulary term with definition
            slides_data.json  ← structured slide data from Google Slides
            slides_notes.pdf  ← two-column PDF: slide image + speaker notes
            slide_01.png …    ← individual slide images
            lesson_<id>_levels.json ← Code.org level data (Panels, Aichat, FreeResponse, Multi, External)
            panels_level_<id>.pdf   ← rendered Panels levels
            external_level_<id>.pdf ← rendered External levels
          videos/
            <video-name>/
              script.json                  ← pipeline state + scenes (the working file)
              script_cleaned.json          ← base64-stripped copy (temp, created by video-html)
              scenes_draft.json            ← draft scenes array (temp, created by video-script)
              scenes/
                scene_01.html …           ← generated HTML slides (self-contained documents)
              audio/
                scene_01.mp3 …            ← TTS audio per scene (Gemini mode)
                voiceover.mp3             ← combined audio file (ElevenLabs mode)
              images/
                generated_image_*.png     ← AI-generated images (Gemini image gen)
              script_assembled_base64.json ← final player-ready file (do not read into context)
              video_archive.zip            ← source archive: script.json + scenes + audio + images
    standalone/
      lessons/                ← lessons not tied to a curriculum unit (user-chosen slugs)

main.py                       ← FastAPI entry point: detects CLOUDSQL_INSTANCE + ARTIFACT_BUCKET env vars; routes to Cloud SQL sessions + GCS artifacts on Cloud Run, SQLite + InMemory locally
Dockerfile                    ← builds from python:3.12-slim; bakes backend/ + generation/units/ + generation/tools/*.py
cloud-run-env.yaml            ← env vars for Cloud Run deployment (gitignored — contains secrets)
DEPLOY_INSTRUCTIONS.md        ← step-by-step Cloud Run + IAP deployment guide
```

---

## Session state

**Local development:** ADK sessions use SQLite (`sessions.db` in the working directory). Artifacts are stored per-session in `.adk/artifacts/` locally.

**Cloud Run:** Sessions are persisted to Cloud SQL (PostgreSQL) when `CLOUDSQL_INSTANCE` is set. Artifacts are stored in the GCS bucket named by `ARTIFACT_BUCKET`. Both survive container restarts and scale-to-zero. Without these env vars, Cloud Run falls back to SQLite + in-memory artifacts — not suitable for production.

`main.py` detects both env vars at startup and configures the appropriate backends automatically. See [GCS_SETUP_INSTRUCTIONS.md](GCS_SETUP_INSTRUCTIONS.md) and [SQL_SETUP_INSTRUCTIONS.md](SQL_SETUP_INSTRUCTIONS.md) for one-time infrastructure setup.
