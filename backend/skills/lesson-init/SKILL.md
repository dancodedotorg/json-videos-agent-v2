---
name: lesson-init
description: Initializes a lesson folder within a unit. Reads unit.json to match and confirm the lesson, then runs init_lesson.py with the lesson ID to create folders and sources.csv. Invoke with /lesson-init <unit-slug> <lesson-name>.
allowed-tools: Bash(python *) Read Glob
metadata:
  argument-hint: "<unit-slug> <lesson-name>"
---

# lesson-init

Initialize a lesson folder at `generation/units/<unit>/lessons/<lesson>/`.

Parse `$ARGUMENTS` as two parts: `UNIT` (first word) and `LESSON_NAME` (everything after the first word).

## Step 1: Match lesson in unit.json

Read `generation/units/$UNIT/unit.json`. Find the lesson whose title best matches LESSON_NAME (fuzzy — "lesson 1", "lesson-1-talking", or "Talking to Machines" should all match "Lesson 1: Talking to Machines").

Derive the canonical folder slug from the matched title. For `"Lesson N: Rest of Title"`, produce `lesson-N-<slugified-rest>`: lowercase the title, strip characters that are not letters, digits, spaces, or hyphens, then collapse runs of spaces and hyphens into a single hyphen:
- `"Lesson 1: Talking to Machines"` → `lesson-1-talking-to-machines`
- `"Lesson 4: Smart or Just Predictable?"` → `lesson-4-smart-or-just-predictable`

Show the match and ask the user to confirm before proceeding:

```
Matched "Lesson 1: Talking to Machines" (id: 9520955)
Folder: generation/units/$UNIT/lessons/lesson-1-talking-to-machines/

Proceed? [y/n]
```

If the user says no, list all available lesson titles from unit.json and stop — ask them to re-run with a corrected name.

If unit.json does not exist, tell the user to run `/unit-init $UNIT` first.

## Step 1.5: Check for existing initialization

Use `Glob` to check if `generation/units/$UNIT/lessons/$LESSON_SLUG/sources.csv` already exists.

If it does, warn:
```
⚠️  This lesson has already been initialized. Re-running will overwrite sources.csv —
     any manual edits will be lost. Continue? [y/n]
```

If the user says no, stop.

## Step 2: Run init_lesson.py with the lesson ID

Use `execute` to run:

```bash
python .agents/skills/lesson-init/scripts/init_lesson.py $UNIT $LESSON_ID
```

Where `$LESSON_ID` is the integer `id` from the matched lesson in unit.json. Print the script output directly.

## Gotchas

- **Re-running always overwrites sources.csv** — `init_lesson.py` regenerates it from scratch from `unit.json`. Any manual edits (resolving `REVIEW:` rows, adding custom entries) are lost. Step 1.5 guards against accidental overwrites.
- **Slug shown in confirmation matches what the script creates** — `init_lesson.py` uses the same derivation algorithm. If there is ever a discrepancy, the script output is authoritative.
