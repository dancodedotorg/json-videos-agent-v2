# 03 — Artifact-Based Source Loading for video-script

## Background

The `video-script` skill reads lesson source materials — slide PDFs, lesson level JSON, objectives, and vocabulary — before generating a voiceover script. Prior to this change, it did so via `read_file` from the `EnvironmentToolset`. That approach had two compounding problems: it could not deliver PDFs as multimodal content to Gemini, and the content it did deliver persisted in session history for the rest of the pipeline, wasting tokens on every subsequent skill turn.

This change introduces a new Python tool (`load_lesson_sources`) that saves source materials as ADK session artifacts, and updates `video-script` to load those artifacts via `load_artifacts` (provided by `LoadArtifactsTool`) instead of reading files directly.

---

## What Changed

### `backend/tools/load_lesson_sources.py` (new)

An async Python tool registered with the agent. When called with `unit` and `lesson` slug, it:

1. Resolves `generation/units/<unit>/lessons/<lesson>/source/` from the project root
2. Checks `list_artifacts()` first — if any artifact with the `<lesson>__` prefix already exists, returns `status: already_loaded` immediately (idempotent)
3. Iterates the source directory:
   - **PDFs** → saved as `<lesson>__<filename>.pdf` with `mime_type="application/pdf"`
   - **JSON files** → base64 image/audio payloads stripped inline (same regex as `base64_clean.py`) before saving as `<lesson>__<filename>.json` with `mime_type="application/json"`; `lesson_*_levels*.json` files are normalized to `<lesson>__lesson_levels.json` regardless of the numeric ID in the filename
   - **Markdown files** → saved as `<lesson>__<filename>.md` with `mime_type="text/plain"`
   - **PNG/JPG images and `_cleaned.json` files** → skipped
4. Returns `{status, artifacts: [...], errors: [...]}` for the agent to inspect

Artifact names use `<lesson>__<filename>` (double underscore, no slashes) to prevent collision if multiple lessons are loaded in the same session.

### `backend/agent.py` (edited)

- Added imports: `LoadArtifactsTool`, `load_lesson_sources`
- Added both to the agent's `tools` list
- Updated the system instruction to describe `load_lesson_sources` and `load_artifacts` and clarify that `read_file` is now reserved for project files like `script.json` (not source materials)

No changes to Runner configuration: `adk web` automatically provisions a local file-backed artifact service at `.adk/artifacts/` by default. No explicit `InMemoryArtifactService` wiring is needed.

### `.agents/skills/video-script/SKILL.md` (edited)

Step 3 ("Read Source Material") replaced with a two-phase artifact approach:

- **Phase A:** Call `load_lesson_sources(unit, lesson)` to ensure artifacts are saved. If it returns an error (source directory missing), the skill stops and tells the user to run `/lesson-ground` first.
- **Phase B:** Call `load_artifacts` with the artifact names returned by Phase A. PDFs are delivered as native multimodal parts; JSON arrives pre-cleaned.

Removed from the skill:
- The `base64_clean.py` instruction for source JSON files (handled by `load_lesson_sources` at save time)
- The 20-page PDF pagination workaround (no longer needed with native multimodal delivery)
- The "JSON source files require preprocessing" Gotcha entry

All other steps (mode selection, target objectives lens, scene generation, `write-scenes.py`, human check-in) are unchanged.

---

## Why Not Store Everything as Artifacts? (The File-System vs. Artifacts Tradeoff)

It is worth explaining why `lesson-ground`'s output (the `source/` folder) was left on disk rather than replaced by artifacts entirely.

**The file system is still the right layer for grounding output** for several reasons:

1. **Durability across sessions.** ADK session artifacts are scoped to a single session. A new chat session starts with no artifacts. The `source/` folder on disk persists indefinitely — you can close the browser, restart `adk web`, and the grounded materials are still there. This is exactly the right behavior for lesson source files, which represent slow-changing reference material fetched from Google Slides/Drive once and reused many times.

2. **Artifacts would just be a copy.** If `lesson-ground` saved to artifacts instead of disk, you would still need to re-load them into every new session anyway — so you haven't avoided the disk; you've just added an artifact layer on top of it. The current design is simpler: disk is authoritative, artifacts are a session-scoped cache of what's already on disk.

3. **Shared across skills.** The `source/` folder is read by `video-init` (to list objectives), by `video-script` (for narration), and potentially by future skills. The file system is a natural shared store that all skills and scripts can access without coordination. If the source lived only in artifacts, each skill would need to load it independently each turn.

4. **`lesson-ground` runs Python scripts** (`ground-lesson.py`, `google-fetch.py`) that write directly to disk — refactoring them to write to artifacts would require threading ADK's async `ToolContext` through subprocess-based Python scripts, which is a significant and unnecessary complication.

In short: the file system is the right durable store for lesson source materials. Artifacts are only the right layer for the *session-scoped in-context delivery* of those materials — which is exactly what this change adds.

---

## Why Artifacts for the Script Stage? (Token and Multimodal Motivation)

Two concrete problems with the prior `read_file` approach motivated this change:

### 1. `read_file` cannot deliver PDFs as multimodal content

`EnvironmentToolset`'s `ReadFile` tool is text-only. When it encounters a PDF, it either fails or returns the raw binary as garbled text. This means Gemini was previously getting no useful signal from slide PDFs — the primary source of visual context for the narration it was generating.

`LoadArtifactsTool` injects artifacts as typed `google.genai.types.Part` objects with their MIME type preserved. Gemini 2.5 Flash natively understands `application/pdf` parts and can read slide images, text, and layout as a multimodal document — exactly as a human would. The 20-page pagination workaround in the old SKILL.md existed because `read_file` was treating PDFs as text and the results were unreliable at scale; that workaround is no longer needed.

### 2. `read_file` results persist in session history, wasting tokens downstream

When the agent calls `read_file` on a large PDF or JSON file during `video-script`, that file's content is stored as a tool result in the ADK session event log. Every subsequent LLM call in the session — `video-html`, `video-audio-tags`, `video-audio`, etc. — includes that full session history in its context window. A single lesson's source materials might be 50–200 KB of text (or much more for base64-heavy JSON before cleaning). That content is completely irrelevant to HTML generation, audio tagging, or audio synthesis, but the model pays for it in input tokens on every turn.

`LoadArtifactsTool` is designed precisely to solve this. From the ADK docs:

> *"When the model calls the `load_artifacts` tool, ADK temporarily appends the selected artifact contents to that request so the model can answer with the file content in context. The loaded artifact content is **not permanently saved back into the session history**, so the model should call the tool again when it needs the same artifact in a later turn."*

This means source material content lives in memory for one turn only. After `video-script` completes, the PDFs and JSON are gone from the active context — subsequent skill turns get a clean context window sized only to what they actually need. At scale, across a full lesson pipeline (six skill turns), this is a meaningful reduction in token cost and a meaningful improvement in response quality for the later stages, which no longer have to reason over irrelevant slide content.

---

## Verification

1. Run `adk web backend/` from the project root
2. Start a session and invoke `/video-script` on a grounded lesson
3. Confirm `load_lesson_sources` is called and returns `status: loaded` with a list of artifact names
4. Confirm `load_artifacts` is called next and PDF/JSON content appears in the model's context (visible in the ADK trace panel)
5. Confirm the generated script quality is equivalent to or better than the prior `read_file` approach (the model now has visual slide context it didn't before)
6. Confirm subsequent skill turns (video-html) do NOT include the PDF bytes in their context (check the ADK event log / token counts in the trace)
7. In the same session, invoke `/video-script` on the same lesson a second time — confirm `load_lesson_sources` returns `status: already_loaded` without re-saving

---

## Files Modified

| File | Change |
|------|--------|
| `backend/tools/load_lesson_sources.py` | Created — new async Python tool |
| `backend/agent.py` | Added `LoadArtifactsTool`, `load_lesson_sources` to tools list; updated system instruction |
| `.agents/skills/video-script/SKILL.md` | Step 3 replaced with artifact-based loading; Gotcha removed |
