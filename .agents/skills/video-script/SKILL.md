---
name: video-script
description: Generates the voiceover script (scene comments and speech) for a video project by reading source materials. Includes human check-ins for mode selection and script approval.
---

# video-script

Generate the voiceover script for a video.

## Progress checklist

- [ ] Path detection + prereq check
- [ ] Mode selection (wait for user)
- [ ] Load source materials as artifacts
- [ ] Apply target_objectives lens
- [ ] Generate scenes (read mode style guide first)
- [ ] Write scenes to script.json via write-scenes.py
- [ ] Human check-in and iteration

## Path detection

Extract UNIT, LESSON, and VIDEO from the user's message. If any are missing, ask for them before continuing.

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
- `target_objectives` (new-style only) — the objectives this video must address
- Confirm `pipeline.grounding == "complete"` before continuing

## Step 2: Mode Selection (ask the user)

Ask the user to choose a generation mode before doing anything:

> **How should I generate the script for "$VIDEO"?**
>
> - **concept** — One scene per slide with detailed narration; explains each slide fully. Best for tutorial/teaching videos.
> - **summary** — Fewer scenes covering key takeaways; groups related slides. Best for overview/review videos.
> - **re-teach** — A remediation video for students who completed the lesson but need reinforcement. Stays grounded in the original lesson; explains concepts more explicitly and walks through student tasks. Best for review/support videos.
> - **co-create** — You provide a custom brief (audience, angle, focus) and I generate scenes accordingly.
>
> Which mode? (concept / summary / re-teach / co-create)

Wait for the user's response before proceeding. If `co-create`, also ask for the brief.

## Step 3: Load Source Material as Artifacts

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

## Step 4: Apply target_objectives lens (new-style videos only)

If `target_objectives` is set in script.json, use those objectives as the **primary lens** for script generation:

- Prioritize content from source materials that directly addresses the target objectives
- Weight vocabulary emphasis toward terms most relevant to the target objectives
- If the source material covers topics beyond the target objectives, de-emphasize or omit those topics in the script (the other videos in this lesson will cover them)
- The script should feel complete and coherent on its own while staying focused on the chosen objectives

## Step 5: Generate Scenes

Before generating, use `load_skill_resource` to read the style guide for the chosen mode and follow all guidance there:

- **concept**: Use `load_skill_resource` to read `references/concept-style-guide.md` in full. That file covers: required intro scene, one scene per slide, handling slides with no speaker notes, scene length targets, tone, and `comment` field conventions.
- **summary**: Use `load_skill_resource` to read `references/summary-style-guide.md` in full. That file covers: required intro scene, grouping criteria, key-takeaway framing, scene length targets, and what to compress or skip.
- **re-teach**: Use `load_skill_resource` to read `references/reteach-style-guide.md` in full. That file covers: required intro scene, structure and length targets, content rules (elaboration pass, activity walkthroughs, no new analogies), lesson-referencing conventions (student actions only, never teacher actions), tone and language, and Question of the Day handling.
- **co-create**: Use `load_skill_resource` to read `references/co-create-style-guide.md` in full. That file covers: what a complete brief contains, defaults for thin briefs, scene structure, tone, and when to flag brief/objective conflicts.

Each scene object:
```json
{
  "comment": "Brief visual description of what this scene should show",
  "speech": "Full narration text the viewer will hear"
}
```

## Step 6: Write to script.json

Write the generated scenes array to a temp file alongside the script, then use `write-scenes.py` to merge it in:

```bash
python .agents/skills/video-script/scripts/write-scenes.py SCRIPT_PATH SCENES_DRAFT_PATH
```

Where `SCENES_DRAFT_PATH` is a JSON file containing only the scenes array (e.g., `generation/units/UNIT/lessons/LESSON/videos/VIDEO/scenes_draft.json`). The script replaces the `scenes` field in `script.json` and sets `pipeline.script = "complete"` atomically — do not manually edit `script.json` to insert scenes.

## Step 7: Human Check-In

Present the generated script to the user in a readable format (numbered list of comment + speech pairs). Then ask:

> Does this script look good? You can ask me to:
> - Revise specific scenes (e.g., "make scene 3 shorter")
> - Add or remove scenes
> - Adjust the tone or level of detail
> - Approve and move on to HTML slides

Iterate on revisions until the user approves. Then tell them:
- "Tell the user to continue with the video-html skill for $UNIT / $LESSON / $VIDEO to generate HTML slides."
