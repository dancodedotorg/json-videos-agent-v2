---
name: video-assemble
description: Assembles the final player-ready script.json by embedding audio as base64 and inlining any local image paths. The output loads directly in the json-video-player.
---

# video-assemble

Produce the final player-ready `script.json` for a video.

## Path detection

Extract UNIT, LESSON, and VIDEO from the user's message, or from session context if continuing from a previous step. Only ask if genuinely unknown.

Use `execute` to list `generation/units/$UNIT/lessons/` and match LESSON to the closest folder name as LESSON_SLUG. If the unit directory doesn't exist, stop with `❌ Unit "$UNIT" not found.` If nothing matches, stop with `❌ No lesson matching "$LESSON" found.` If you fuzzy-matched, show `⚠️  Resolved "$LESSON" → "$LESSON_SLUG"`.

- Video root: `generation/units/$UNIT/lessons/$LESSON_SLUG/videos/$VIDEO/`

All steps below use VIDEO_ROOT derived above.
SCRIPT_PATH = `<VIDEO_ROOT>/script.json`
OUTPUT_PATH = `<VIDEO_ROOT>/script_assembled_base64.json`

## Gotchas

- **Do not read `script.json` directly** — it may contain base64 HTML content that floods the context window. All operations use Python scripts.
- **`script.json` is never modified** — the script always writes to `script_assembled_base64.json`.
- **Image paths must be absolute** — `<img src="...">` paths are only embedded if they start with `/`, `file://`, or a Windows drive letter (`C:\`). Relative paths are silently skipped with no warning.
- **Audio paths are resolved relative to `script.json`'s directory** (VIDEO_ROOT), not the working directory. This is correct for both old and new folder structures.
- **Missing audio files produce a warning, not an error** — `embed-data.py` prints `WARNING: file not found, skipping` to stderr and continues. Check stderr if audio is missing from the output.
- **The output file may be large** (multi-MB) — this is expected when images and audio are embedded as base64.

## Steps

### 1. Embed all assets (images + audio)

Use `execute` to run:
```bash
python backend/skills/video-assemble/scripts/embed-data.py <SCRIPT_PATH> <OUTPUT_PATH>
```

This writes `script_assembled_base64.json` with all local assets embedded as base64 data URIs in a single pass:
- `<img>` tags with absolute file paths in `scenes[].html` → inline data URIs
- `scenes[].audio` paths (per-scene mode) → inline data URIs
- Top-level `audio` path (combined mode) → inline data URI
- Fake mode (`tts.mode == "fake"`) — audio skipped automatically
- Sets `pipeline.assembled = true` in the output

### 2. Report to user

```
✅ Assembly complete.

Output:  <OUTPUT_PATH>
Archive: <VIDEO_ROOT>/video_archive.zip
Source:  <SCRIPT_PATH> (unchanged)

Note: the assembled file may be large due to embedded audio and images — this is expected.
```

### 3. Save output as downloadable artifacts

Call `save_video_output(unit=UNIT, lesson=LESSON_SLUG, video=VIDEO)`.

Do NOT read script.json or script_assembled_base64.json into context — they are too large and will exceed token limits.

Then tell the user:

```
📦 Your output files are saved as artifacts and are ready to download from the artifacts panel:
  - script_assembled_base64.json — the player-ready file (load this in the json-video-player)
  - video_archive.zip — source files (script.json + scenes/, images/, audio/) for re-editing

⚠️  These artifacts exist only for this session. Download them before closing.

To re-edit later: unzip video_archive.zip — it contains the original script.json and all
  scene HTML, image, and audio files. Re-run the pipeline from whichever stage you changed.

Ask me if you have any questions about the output files or next steps.
```
