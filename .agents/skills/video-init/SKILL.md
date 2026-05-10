---
name: video-init
description: Initializes a new video project folder within an existing grounded lesson. Checks lesson grounding, prompts objective selection, creates the video folder with audio/images/scenes, and writes an initial script.json.
---

# video-init

Initialize a new video at `generation/units/<unit>/lessons/<lesson>/videos/<video>/`.

Extract UNIT, LESSON, and VIDEO from the user's message. If any are missing, ask for them before continuing.

## Step 0: Resolve lesson slug

Use `execute` to list `generation/units/$UNIT/lessons/`:

Match LESSON against the folder names to determine LESSON_SLUG. If the unit directory doesn't exist, stop with `❌ Unit "$UNIT" not found.` If no folder matches, stop with `❌ No lesson matching "$LESSON" found.` If ambiguous, ask the user to clarify.

If you fuzzy-matched (the input wasn't the exact folder name), show:
```
⚠️  Resolved "$LESSON" → "$LESSON_SLUG"
```

Use `LESSON_SLUG` for all subsequent paths.

## Step 1: Verify lesson grounding is complete

Read `generation/units/$UNIT/lessons/$LESSON_SLUG/lesson-state.json`.

If the file does not exist, or `grounding != "complete"`, exit with:
```
❌ Lesson "$LESSON" has not been grounded yet.
   Run /lesson-ground $UNIT $LESSON first to fetch source materials.
```

## Step 2: Load objectives

Read `generation/units/$UNIT/lessons/$LESSON/source/objectives.md` to get the available objectives.

If it doesn't exist, fall back to reading objectives from `generation/units/$UNIT/unit.json` (find the lesson by slug match on title).

Show the user a numbered list of available objectives, then a lettered list of vocabulary terms, and ask:

```
Which objectives should this video emphasize? (enter numbers, e.g. 1,3)

  1. Analyze patterns in AI-generated responses...
  2. Experiment with different prompts...
  ...

Which vocabulary terms should this video define? (enter letters, or press Enter to auto-assign from objectives)

  a. abstraction
  b. artificial intelligence (AI)
  ...
```

Wait for both responses. Store as TARGET_OBJECTIVES and TARGET_VOCABULARY. If the user skips vocabulary, assign terms whose words appear in the selected objective texts.

## Step 3: Write script.json

The `write_file` tool creates parent directories automatically, so no separate folder creation step is needed.

Use `write_file` to write `generation/units/$UNIT/lessons/$LESSON/videos/$VIDEO/script.json`:

```json
{
  "video_name": "$VIDEO",
  "unit": "$UNIT",
  "lesson": "$LESSON",
  "target_objectives": [<TARGET_OBJECTIVES array>],
  "target_vocabulary": [<TARGET_VOCABULARY array>],
  "width": 1600,
  "height": 900,
  "pipeline": {
    "grounding": "complete",
    "script": "pending",
    "audio_tags": "pending",
    "audio": "pending",
    "html": "pending",
    "assembled": false
  },
  "grounding": {},
  "tts": {},
  "scenes": []
}
```

`pipeline.grounding` is pre-set to `"complete"` because grounding happens at the lesson level.

## Step 5: Confirm

Print:
```
✅ Video "$VIDEO" initialized in lesson "$LESSON".

  Location: generation/units/$UNIT/lessons/$LESSON/videos/$VIDEO/
  Target objectives: <N> selected
  Source materials: shared from generation/units/$UNIT/lessons/$LESSON/source/

Next: continue with the video-script skill for $UNIT / $LESSON / $VIDEO
```
