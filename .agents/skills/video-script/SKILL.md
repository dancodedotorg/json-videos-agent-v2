---
name: video-script
description: Generates the voiceover script (scene comments and speech) for a video project by reading source materials. Includes human check-ins for mode selection and script approval. Invoke with /video-script <unit-slug> <lesson-slug> <video-name>.
allowed-tools: Read Write Bash(python:*)
metadata:
  disable-model-invocation: "true"
  argument-hint: "<unit-slug> <lesson-slug> <video-name>"
---

# video-script

Generate the voiceover script for a video.

## Progress checklist

- [ ] Path detection + prereq check
- [ ] Mode selection (wait for user)
- [ ] Read all source material
- [ ] Apply target_objectives lens
- [ ] Generate scenes (read mode style guide first)
- [ ] Write scenes to script.json via write-scenes.py
- [ ] Human check-in and iteration

## Path detection

Parse `$ARGUMENTS` (3 words): UNIT=first, LESSON=second, VIDEO=third

List `generation/units/$UNIT/lessons/` and match LESSON to the closest folder name as LESSON_SLUG. If the unit directory doesn't exist, stop with `❌ Unit "$UNIT" not found.` If nothing matches, stop with `❌ No lesson matching "$LESSON" found.` If you fuzzy-matched, show `⚠️  Resolved "$LESSON" → "$LESSON_SLUG"`.

- Script path: `generation/units/$UNIT/lessons/$LESSON_SLUG/videos/$VIDEO/script.json`
- Source path: `generation/units/$UNIT/lessons/$LESSON_SLUG/source/`

All steps below use SCRIPT_PATH and SOURCE_PATH derived above.

## Prerequisites

- `pipeline.grounding` must be `"complete"` in `script.json`
- Source files must exist at SOURCE_PATH

## Gotchas

- **Slides with no speaker notes:** synthesize narration from the slide title and visible content — do not skip the slide.
- **JSON source files require preprocessing:** always run `base64_clean.py` before reading any `.json` in SOURCE_PATH. Skipping this step will likely cause token overload or read errors.
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

## Step 3: Read Source Material

Start by listing all files in SOURCE_PATH so you know exactly what exists before deciding what to read — this catches manually-added files that weren't produced by the fetch pipeline.

Read **all** source files for complete grounding context. Run base64_clean.py on JSON files as a safety precaution before reading.

**PDF files** (read directly — the Read tool supports PDFs up to 20 pages per request):
- If `source/slides_notes.pdf` exists: read it first — it contains slide images + speaker notes side-by-side, giving complete visual and text context for each slide. For presentations over 20 slides, read pages 1-20 first, then continue in 20-page increments.
- If `source/panels_level_*.pdf` files exist: read them — each is one Code.org Panels level (a slideshow), showing panel images alongside text content.
- If `source/external_level_*.pdf` files exist: read them — each is one Code.org External level rendered as a full HTML page with images inlined.
- If any other `source/*.pdf` files exist (e.g. Google Doc exports from `google_doc` type): read those too, using page ranges for large files.

**JSON files** (run base64_clean.py first):
- If `source/slides_data.json` exists: run `python scripts/base64_clean.py <SOURCE_PATH>/slides_data.json` and read the `_cleaned.json` output.
- If `source/lesson_*_levels.json` exists: run `python scripts/base64_clean.py` on it and read the `_cleaned` version.

**Markdown files** (read directly):
- If `source/*.md` files exist: read those — this includes `objectives.md` and `vocabulary.md`.

Do NOT read `source/slide_NN.png` or other image files.

When `lesson_*_levels.json` is the primary source, use the level content to understand the lesson structure. Each entry has a `type` and relevant content fields:
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

Before generating, read the style guide for the chosen mode and follow all guidance there:

- **concept**: Read `references/concept-style-guide.md` in full. That file covers: required intro scene, one scene per slide, handling slides with no speaker notes, scene length targets, tone, and `comment` field conventions.
- **summary**: Read `references/summary-style-guide.md` in full. That file covers: required intro scene, grouping criteria, key-takeaway framing, scene length targets, and what to compress or skip.
- **re-teach**: Read `references/reteach-style-guide.md` in full. That file covers: required intro scene, structure and length targets, content rules (elaboration pass, activity walkthroughs, no new analogies), lesson-referencing conventions (student actions only, never teacher actions), tone and language, and Question of the Day handling.
- **co-create**: Read `references/co-create-style-guide.md` in full. That file covers: what a complete brief contains, defaults for thin briefs, scene structure, tone, and when to flag brief/objective conflicts.

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
python scripts/write-scenes.py SCRIPT_PATH SCENES_DRAFT_PATH
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
- "Run /video-html $UNIT $LESSON $VIDEO to generate HTML slides."
