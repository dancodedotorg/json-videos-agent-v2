---
name: unit-init
description: Initializes a new curriculum unit folder, fetches lesson IDs and unit resources from Code.org, and generates unit.json. One-time setup per unit.
allowed-tools: Bash(python *) Bash(mkdir *) Read Write
metadata:
  disable-model-invocation: "true"
  argument-hint: "<unit-slug>"
---

# unit-init

Initialize a curriculum unit at `generation/units/$ARGUMENTS/`.

The unit slug is the URL slug used on studio.code.org — e.g., `problem-solving-with-ai` for `studio.code.org/s/problem-solving-with-ai`.

## Gotchas

- **Manual fallback requires Tampermonkey** — if Step 2 exits with code 2, the user must have the Tampermonkey browser extension installed before attempting the manual step. If they don't have it, they need to install it first.
- **Grounding requires Google credentials** — `ground-all.py` (Step 5) requires `GOOGLE_API_KEY` and `GOOGLE_SERVICE_ACCOUNT_JSON` in `generation/tools/.env`. If the user says credentials aren't configured, skip the grounding offer entirely.

## Step 1: Create folder structure

Use `execute` to run:
```bash
mkdir -p generation/units/$ARGUMENTS
```

## Step 2: Fetch lessons and resources

Use `execute` to run the fetch script, which saves `lessons.json` and `resources.json` to `generation/units/$ARGUMENTS/`:

```bash
python .agents/skills/unit-init/scripts/fetch_unit.py $ARGUMENTS
```

The script prints the lesson list on success.

If it exits with code 2, relay the instructions the script printed to the user exactly as printed, then stop. Do not proceed to Step 3 until the user confirms that `resources.json` exists.

## Step 3: Generate unit.json

Use `execute` to run `filter_resources.py` to produce the clean unit.json:

```bash
python .agents/skills/unit-init/scripts/filter_resources.py generation/units/$ARGUMENTS/resources.json generation/units/$ARGUMENTS/lessons.json
```

This writes `generation/units/$ARGUMENTS/unit.json` directly.

## Step 4: Confirm

Print a summary:
```
✅ Unit "$ARGUMENTS" initialized.

  unit.json: N lessons with resources, vocabulary, and objectives
  Location:  generation/units/$ARGUMENTS/

Next steps:
  For each lesson you want to generate videos for:
    /lesson-init $ARGUMENTS <lesson-name>
```

## Step 5: Offer bulk lesson initialization

Ask the user:

```
Would you like to initialize all lessons in this unit now?
This will run init_all_lessons.py and create a folder for every lesson in unit.json.

Reply "yes" to proceed, or "no" to skip.
```

If the user says **yes**, use `execute` to run:

```bash
python .agents/skills/unit-init/scripts/init_all_lessons.py $ARGUMENTS
```

Then confirm:

```
✅ All lessons initialized.
```

Then ask:

```
Would you also like to ground all lessons now?
This fetches source materials (slides, docs, objectives, vocabulary) for every lesson.
It requires Google API credentials to be configured in generation/tools/.env.

Reply "yes" to proceed, or "no" to skip.
```

If the user says **yes**, use `execute` to run:

```bash
python .agents/skills/unit-init/scripts/ground-all.py $ARGUMENTS
```

Then confirm:

```
✅ All lessons grounded. You can now run /lesson-plan <unit> <lesson> for any lesson.
```

If the user says **no** to grounding, or **no** to bulk init, output the Step 4 confirmation block as the final response with no additional message.
