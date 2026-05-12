---
name: lesson-ground
description: Fetches all lesson-level source materials (slides, docs, level content, objectives, vocabulary) into the shared lesson source/ folder. Must be run before any video in the lesson can be initialized — use this when starting work on a new lesson, before running /lesson-plan, /video-init, or /video-create. Invoke with /lesson-ground <unit-slug> <lesson-slug>.
allowed-tools: Bash(python *) Glob Read Write Edit
metadata:
  argument-hint: "<unit-slug> <lesson-slug>"
---

# lesson-ground

Fetch all source materials for `generation/units/<unit>/lessons/<lesson>/source/`.

Parse `$ARGUMENTS` as two parts: `UNIT` (first word) and `LESSON` (everything after the first word).

---

## Prerequisites

All generation scripts require Python packages. If you get a `ModuleNotFoundError`, run:
```bash
pip install -r generation/tools/requirements.txt
```

---

## Step 0: Resolve lesson slug

Use `Glob` with pattern `generation/units/$UNIT/lessons/*/` to list available lesson folders.

If the unit directory yields no results, stop with `❌ Unit "$UNIT" not found.`

Match LESSON to a folder name using this priority order:
1. Exact match (case-insensitive)
2. Prefix match (folder name starts with LESSON)
3. Substring match (folder name contains LESSON)

If multiple folders match at the same tier, list them and ask the user to choose. If nothing matches at any tier, stop with `❌ No lesson matching "$LESSON" found.` If you fuzzy-matched, show `⚠️  Resolved "$LESSON" → "$LESSON_SLUG"`.

Use `LESSON_SLUG` for all subsequent paths.

---

## Step 1: Check existing grounding

Read `generation/units/$UNIT/lessons/$LESSON_SLUG/lesson-state.json` if it exists.

If `grounding == "complete"`, ask the user:
```
Source materials were already fetched on <grounded_at>.
Re-fetch everything? This will overwrite existing source files. [y/n]
```

If no: stop. If yes: pass `--force` when calling the script in Step 3.

---

## Step 2: Review and validate sources.csv

Read `generation/units/$UNIT/lessons/$LESSON_SLUG/sources.csv`.

If the file doesn't exist or has no rows beyond the header, stop with:
```
❌ sources.csv not found or empty. Run /lesson-init $UNIT $LESSON_SLUG first.
```

Inspect every row yourself before the script runs. You are looking for:

**Type errors.** Valid types are: `google_slides`, `google_doc`, `level_summary`, `google_drive_file`, `objective`, `vocabulary`. If you see anything else, tell the user what you found and what you think it should be:
```
⚠️  Row "$DESCRIPTION" has type "$RAW_TYPE" — did you mean "$SUGGESTED_TYPE"? [y / enter correction / skip row]
```
Wait for confirmation before proceeding. Do not silently correct anything. If the user enters a correction, use `Edit` to update the type value in that row of `sources.csv` before continuing.

**REVIEW-flagged rows.** If a description starts with `REVIEW:`, show it to the user:
```
⚠️  Row flagged for manual review: "$DESCRIPTION"
     Skip this row and continue? [y/n]
```
If the user says yes: use `Edit` to remove that row from sources.csv before running the script. The script does not filter REVIEW rows itself — deleting the row is the only way to skip it.

Note: rows with type `google_drive_file` are always auto-flagged with `REVIEW:` by init_lesson.py because they cannot be auto-fetched. The user must download these files manually and either remove the row or update it with a local path.

**Empty values.** If a fetchable row (`google_slides`, `google_doc`, `level_summary`, `google_drive_file`) has no value, tell the user and stop:
```
❌ Row "$DESCRIPTION" (type: $TYPE) has no URL or ID. Fix sources.csv and re-run.
```

Once all rows have been inspected and any issues resolved, proceed. The script in Step 3 will fail hard on any remaining problems — that is intentional.

---

For the full list of output files produced by each type, see [source-types.md](references/source-types.md).

## Step 3: Run ground-lesson.py

Use `execute` to run:
```bash
python backend/skills/lesson-ground/scripts/ground-lesson.py $UNIT $LESSON_SLUG [--force] [--dry-run]
```

Pass `--force` if the user confirmed a re-fetch in Step 1.

Surface all script stdout to the user as it completes — it shows which sources were fetched and any warnings.

**Interpret the exit code:**

| Code | Meaning |
|------|---------|
| `0`  | All sources fetched — proceed to Step 4 |
| `1`  | One or more sources failed — show which sources failed from the output. lesson-state.json is written as `"partial"`. The user can fix sources.csv and re-run without `--force` to retry. |
| `2`  | Already grounded, `--force` not passed — this shouldn't happen if Step 1 ran correctly; warn the user |

---

## Step 4: Confirm

Read `sources_fetched` from `generation/units/$UNIT/lessons/$LESSON_SLUG/lesson-state.json` to get `<N>`.

```
✅ Lesson grounding complete for "$LESSON_SLUG".

  Source materials saved to:
    generation/units/$UNIT/lessons/$LESSON_SLUG/source/

  Fetched: <N> sources
  lesson-state.json: written

Next: /lesson-plan $UNIT $LESSON_SLUG
  (or /video-init $UNIT $LESSON_SLUG <video-name> if adding a single video to an existing plan)
```

---

## Gotchas

- **REVIEW rows are not filtered by the script** — the only way to skip a REVIEW row is to remove it from sources.csv before running (Step 2 handles this).
- **`google_drive_file` always flags REVIEW** — init_lesson.py cannot auto-fetch Google Drive files. The user must download them manually and either remove the row from sources.csv or update the value with a local file path.
- **Exit code 1 (partial) still writes lesson-state.json** — the status is set to `"partial"`, not `"complete"`. Fix the failing sources in sources.csv and re-run without `--force` to retry only the failed ones.
- **Credentials must be present in `generation/tools/.env`** — specifically `GOOGLE_SERVICE_ACCOUNT_JSON` (base64-encoded service account JSON) and `GOOGLE_API_KEY`. If the script exits on the first fetch with a credentials error, check this file first.
- **`objective` and `vocabulary` rows are not fetched** — they are written directly to `source/objectives.md` and `source/vocabulary.md` from the values in `sources.csv`. No URL or ID is needed for these row types.
