---
name: video-script
description: Generates the voiceover script (scene comments and speech) for a video project by reading source materials and the video's planned mode. Includes a human check-in for script approval.
---

# video-script

Generate the voiceover script for a video.

## Progress checklist

- [ ] Path detection + prereq check
- [ ] Load source materials as artifacts
- [ ] Apply target_objectives lens
- [ ] Generate scenes (read mode style guide first)
- [ ] Write scenes to script.json via write-scenes.py
- [ ] Human check-in and iteration

## Path detection

Extract UNIT, LESSON, and VIDEO from the user's message, or from session context if continuing from a previous step. Only ask if genuinely unknown.

Use `execute` to list `generation/units/$UNIT/lessons/` and match LESSON to the closest folder name as LESSON_SLUG. If the unit directory doesn't exist, stop with `❌ Unit "$UNIT" not found.` If nothing matches, stop with `❌ No lesson matching "$LESSON" found.` If you fuzzy-matched, show `⚠️  Resolved "$LESSON" → "$LESSON_SLUG"`.

- Script path: `generation/units/$UNIT/lessons/$LESSON_SLUG/videos/$VIDEO/script.json`
- Source path: `generation/units/$UNIT/lessons/$LESSON_SLUG/source/`

All steps below use SCRIPT_PATH and SOURCE_PATH derived above.

## Prerequisites

- `pipeline.grounding` must be `"complete"` in `script.json`
- Source files must exist at SOURCE_PATH

## Gotchas

- **Slides with no speaker notes:** synthesize narration from the slide title and visible content — do not skip the slide.
- **`write-scenes.py` writes to disk:** write scenes to a temp `scenes_draft.json` in the video folder, then run the script. Do not manually edit `script.json` to insert scenes.

## Step 1: Read script.json metadata

Read SCRIPT_PATH. Extract:
- `target_objectives` — the objectives this video must address
- `mode` — the generation mode (concept / summary / re-teach / co-create)
- `brief` — the co-create brief string, or null

Confirm `pipeline.grounding == "complete"` before continuing.

## Step 2: Load Source Material as Artifacts

**Phase A — Ensure artifacts are loaded:**

Call `load_lesson_sources(unit=UNIT, lesson=LESSON_SLUG)`. This tool reads source files from disk and saves them as session artifacts. It is idempotent — if artifacts for this lesson already exist in the session it returns `status: already_loaded` immediately. If it returns `status: error`, stop and tell the user to run `/lesson-ground $UNIT $LESSON_SLUG` first.

**Phase B — Load artifacts into context:**

Use `load_artifacts` to retrieve the source files by their artifact names. Artifact names follow the pattern `<LESSON_SLUG>__<filename>`. Use the list returned by `load_lesson_sources` (or load all artifacts with the `<LESSON_SLUG>__` prefix) to know what is available. Load all of them.

Key artifact names to expect:
- `<LESSON_SLUG>__slides_notes.pdf` — slide images + speaker notes; load this first when present
- `<LESSON_SLUG>__slides_data.json` — structured slide data (base64 already cleaned)
- `<LESSON_SLUG>__lesson_levels.json` — lesson level data (base64 already cleaned)
- `<LESSON_SLUG>__panels_level_*.pdf` — Code.org Panels levels
- `<LESSON_SLUG>__external_level_*.pdf` — Code.org External levels
- `<LESSON_SLUG>__objectives.md` — lesson objectives
- `<LESSON_SLUG>__vocabulary.md` — vocabulary terms

PDFs are injected as native multimodal content — Gemini reads them in full without page-range limits. JSON files have base64 payloads pre-stripped by `load_lesson_sources`, so no `base64_clean.py` step is needed.

Do NOT use `read_file` for source materials — use `load_artifacts` instead.

When `lesson_levels.json` is the primary source, use the level content to understand the lesson structure. Each entry has a `type` and relevant content fields:
- `Panels`: slide-style content with `text` (markdown) and optional `imageUrl`
- `Aichat`: AI chat activity with `longInstructions` describing the student task
- `FreeResponse`: reflection prompt with `longInstructions` and optional `teacherMarkdown`
- `Multi`: multiple choice question with `questions[].text` and `answers[].text`/`correct`
- `External`: standalone markdown page with `markdown` content

## Step 3: Apply target_objectives lens (new-style videos only)

If `target_objectives` is set in script.json, use those objectives as the **primary lens** for script generation:

- Prioritize content from source materials that directly addresses the target objectives
- Weight vocabulary emphasis toward terms most relevant to the target objectives
- If the source material covers topics beyond the target objectives, de-emphasize or omit those topics in the script (the other videos in this lesson will cover them)
- The script should feel complete and coherent on its own while staying focused on the chosen objectives

## Step 4: Generate Scenes

Before generating, use `load_skill_resource` to read the style guide for the mode stored in `script.json`:

- **concept**: load `references/concept-style-guide.md`
- **summary**: load `references/summary-style-guide.md`
- **re-teach**: load `references/reteach-style-guide.md`
- **co-create**: load `references/co-create-style-guide.md`

For **co-create**: use the style guide for structural rules and scene guardrails; use the `brief` field from `script.json` for creative direction (audience, angle, tone, length). If `brief` is null on a co-create video, apply the defaults from the co-create style guide.

For **all modes**: if `brief` is non-null, incorporate it as supplemental guidance alongside the reference doc.

Each scene object:
```json
{
  "comment": "Brief visual description of what this scene should show",
  "speech": "Full narration text the viewer will hear"
}
```

## Step 5: Write to script.json

Write the generated scenes array to a temp file alongside the script, then use `execute` to run `write-scenes.py` to merge it in:

```bash
python backend/skills/video-script/scripts/write-scenes.py SCRIPT_PATH SCENES_DRAFT_PATH
```

Where `SCENES_DRAFT_PATH` is a JSON file containing only the scenes array (e.g., `generation/units/UNIT/lessons/LESSON/videos/VIDEO/scenes_draft.json`). The script replaces the `scenes` field in `script.json` and sets `pipeline.script = "complete"` atomically — do not manually edit `script.json` to insert scenes.

## Step 6: Human Check-In

Present the generated script to the user in a readable format (numbered list of comment + speech pairs). Then ask:

> Does this script look good? You can:
> - **Approve it** and move on to HTML slides
> - **Revise specific scenes** ("make scene 3 shorter", "scene 2 feels too technical")
> - **Ask why** I structured it a certain way or how it maps to the lesson objectives
> - **Add or remove scenes**
> - **Adjust the tone or level of detail** for the whole script
>
> There's no rush — iterate until you're happy with it.

Iterate on revisions until the user approves. Then print:

```
Script approved.

Next: video-html will generate an HTML slide for each scene. You'll go through
  two check-in rounds:
    1. Scene plan — visual approach (text layout, image gen, or SVG) per scene
    2. Content spec — exact copy and visuals per slide

  Ready to generate the HTML slides? Say yes to continue, or ask any questions about the script first.
```
