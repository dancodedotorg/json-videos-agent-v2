---
name: video-assemble
description: Assembles the final player-ready script.json by embedding audio as base64 and inlining any local image paths. The output loads directly in the json-video-player. Invoke with /video-assemble <unit-slug> <lesson-slug> <video-name>.
allowed-tools: Bash(python *) Read Write
metadata:
  disable-model-invocation: "true"
  argument-hint: "<unit-slug> <lesson-slug> <video-name>"
---

# video-assemble

Produce the final player-ready `script.json` for a video.

## Path detection

Parse `$ARGUMENTS` (3 words): UNIT=first, LESSON=second, VIDEO=third

List `generation/units/$UNIT/lessons/` and match LESSON to the closest folder name as LESSON_SLUG. If the unit directory doesn't exist, stop with `❌ Unit "$UNIT" not found.` If nothing matches, stop with `❌ No lesson matching "$LESSON" found.` If you fuzzy-matched, show `⚠️  Resolved "$LESSON" → "$LESSON_SLUG"`.

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

```bash
python .claude/skills/video-assemble/scripts/embed-data.py <SCRIPT_PATH> <OUTPUT_PATH>
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
Source:  <SCRIPT_PATH> (unchanged)

To preview: open index.html in the player (via http-server), click "Load JSON",
and select script_assembled_base64.json.

Note: the assembled file may be large due to embedded audio and images — this is expected.
```
