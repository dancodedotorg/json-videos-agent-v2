# 02 — script.json Pipeline Improvements

## Background

After auditing the video generation pipeline, three structural issues were identified with how `script.json` is read and written across the six pipeline stages (`video-script` → `video-html` → `video-audio-tags` → `video-audio` → `video-assemble`).

---

## Problem 1: HTML Bloated script.json Throughout the Pipeline

**What was wrong:** The `video-html` skill generated HTML slides and immediately copied them into `script.json` via `insert-slides.py`. This made script.json 10–15x larger (3–10 KB → 36–56 KB) for every stage that came after — audio tags, audio generation, orchestration — even though none of those stages ever read `scenes[].html`. The HTML already existed on disk in `scenes/scene_NN.html` files, so the copy inside script.json was purely redundant.

**What was changed:**
- `video-html/SKILL.md` — Removed Step 10 (the `insert-slides.py` call) and its checklist entry. Added a note in Step 9 explaining that HTML is intentionally not inserted into script.json; `embed-data.py` reads it from `scenes/` at assembly time.
- `video-assemble/scripts/embed-data.py` — Added a fallback in the image-embedding loop: if `scenes[].html` is empty, load the HTML from `scenes/scene_NN.html` before embedding images. Backward compatible — existing videos with HTML already in script.json continue to work unchanged.

**Result:** script.json stays 3–10 KB throughout the entire pipeline until final assembly. The LLM can read the file directly without any stripping gymnastics.

---

## Problem 2: Non-Atomic Writes (Crash Risk)

**What was wrong:** All five pipeline scripts that wrote script.json in-place used the same unsafe pattern: open the file for writing (which immediately truncates it), then write the JSON. A crash, kill signal, or disk error between those two operations would leave script.json empty or partially written — with no way to recover the prior state short of redoing the pipeline stage.

**What was changed** — identical fix applied to all five scripts:
- `video-script/scripts/write-scenes.py`
- `video-html/scripts/insert-slides.py`
- `video-html/scripts/update-pipeline.py`
- `video-audio/scripts/elevenlabs-gen.py`
- `video-audio/scripts/gemini-audio-gen.py`

Each write was replaced with a temp-file + rename pattern:
```python
tmp = script_path.with_suffix(".tmp")
tmp.write_text(json.dumps(data, ...), encoding="utf-8")
tmp.replace(script_path)  # atomic on POSIX
```
`Path.replace()` is atomic on POSIX — the original file is never visible in a partially-written state. The old file remains intact until the new one is fully written.

---

## Problem 3: No Way to Read or Write Specific Fields

**What was wrong:** Any time a skill or the ADK backend needed to check a single pipeline flag or edit one scene's speech, it had to load the entire script.json, make the change in memory, and write the whole file back. On a 56 KB file with embedded HTML, this means the LLM is reading thousands of lines of irrelevant HTML just to access `pipeline.audio`. It also creates risk: if the LLM reconstructs the JSON slightly differently (whitespace, ordering), it can silently corrupt fields it wasn't supposed to touch.

**What was created:** `generation/tools/script_tool.py` — a new shared utility with three commands:

| Command | Purpose |
|---|---|
| `get script.json pipeline.script` | Read a single value by dot-notation path |
| `set script.json pipeline.audio complete` | Write a single scalar value atomically |
| `view script.json [--omit html,elevenlabs,gemini]` | Pretty-print with large scene fields replaced by `<omitted>` |

The `view` command drops a 56 KB post-HTML script.json to ~6 KB — small enough to read directly into LLM context without any stripping. The `set` command uses the same atomic temp+rename write as the fixes in Problem 2. Path syntax supports nested keys and list indices: `scenes.2.speech`, `tts.provider`, `pipeline.assembled`.

---

## Files Changed

| File | Change |
|---|---|
| `.agents/skills/video-html/SKILL.md` | Removed Step 10 (insert-slides call); updated Step 9 note |
| `.agents/skills/video-assemble/scripts/embed-data.py` | Added `scenes/` folder fallback for HTML at assembly time |
| `.agents/skills/video-script/scripts/write-scenes.py` | Atomic write |
| `.agents/skills/video-html/scripts/insert-slides.py` | Atomic write |
| `.agents/skills/video-html/scripts/update-pipeline.py` | Atomic write |
| `.agents/skills/video-audio/scripts/elevenlabs-gen.py` | Atomic write |
| `.agents/skills/video-audio/scripts/gemini-audio-gen.py` | Atomic write |
| `generation/tools/script_tool.py` | **New** — get / set / view accessor utility |
