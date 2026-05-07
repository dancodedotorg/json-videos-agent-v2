---
name: video-create
description: Orchestrates the full video generation pipeline from init through assembly. Runs all stages in sequence, pausing at each human check-in point. Invoke with /video-create <unit-slug> <lesson-slug> <video-name>.
allowed-tools: Read Bash(python *) Write
metadata:
  disable-model-invocation: "true"
  argument-hint: "<unit-slug> <lesson-slug> <video-name>"
---

# video-create

Run the full video generation pipeline for a video.

## Path detection

Parse `$ARGUMENTS` (3 words): UNIT=first, LESSON=second, VIDEO=third

- Script path: `generation/units/$UNIT/lessons/$LESSON/videos/$VIDEO/script.json`
- Lesson state: `generation/units/$UNIT/lessons/$LESSON/lesson-state.json`

## Pre-conditions check (new-style only)

Before starting the pipeline for a new-style video, verify the lesson is grounded:

Read `generation/units/$UNIT/lessons/$LESSON/lesson-state.json`. If it doesn't exist or `grounding != "complete"`, exit with:

```
❌ Lesson "$LESSON" has not been grounded.
   Run /lesson-ground $UNIT $LESSON first, then re-run this command.
```

## Pipeline Overview

```
Stage 0: /video-init       → scaffold video folder, select target objectives
Stage 1: (grounding done)  → lesson source/ is the grounding
Stage 2: /video-script     → generate voiceover script (check-in: approve script)
Stage 3: /video-html       → evaluate scenes, generate HTML slides (check-in: script edits if proposed, mode, scene plan)
Stage 4: /video-audio-tags → add expression tags (check-in: approve tags)
Stage 5: /video-audio      → generate audio (check-in: voice + real/fake)
Stage 6: /video-assemble   → embed assets, finalize JSON
```

## Execution

1. Read the script.json (SCRIPT_PATH) if it exists to check `pipeline` status. If the folder doesn't exist, start from Stage 0.

2. For each incomplete stage (where `pipeline.<stage> != "complete"` or `assembled != true`), execute that stage's logic following its SKILL.md instructions. Load the relevant skill file to get the exact steps.

   - When running stages, pass the full argument string `$UNIT $LESSON $VIDEO` to each sub-skill so they resolve paths correctly.

3. Between stages, pause and confirm with the user before proceeding to the next stage.

4. At stages with explicit human check-ins (script, audio-tags, audio, html), follow the check-in instructions from those skills exactly — do not skip them.

## Resuming

If run on a project that's already partially complete, skip completed stages and pick up from where the pipeline left off. Report current status first:

```
📋 "$VIDEO" pipeline status:
  ✅ grounding
  ✅ script
  ⏳ html (next)
  ⏸ audio_tags
  ⏸ audio
  ⏸ assembled
```

## Important: pre-pipeline steps are NOT part of this skill

`/unit-init`, `/lesson-init`, and `/lesson-ground` must be run **before** `/video-create`. This skill does not orchestrate those steps — they are one-time setup actions at the unit and lesson level.

If those steps haven't been completed, this skill will detect it in the pre-conditions check and tell the user what to run first.
