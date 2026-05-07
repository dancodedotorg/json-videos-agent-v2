---
name: lesson-plan
description: Analyzes lesson source materials and objectives to recommend a video plan, then initializes all video folders from the approved plan. Use when setting up a new lesson — do not use /video-init after running this skill.
allowed-tools: Read Write Bash(python *) Glob
metadata:
  argument-hint: "<unit-slug> <lesson-slug>"
---

# lesson-plan

Analyze a lesson's source materials and generate a recommended video plan — a set of named videos, each covering a specific cluster of objectives. Once the user approves a plan, write lesson-plan.json and initialize all video folders.

Parse `$ARGUMENTS` as two parts: `UNIT` (first word) and `LESSON` (everything after the first word).

## Step 0: Resolve lesson slug

Use `Glob` with pattern `generation/units/$UNIT/lessons/*/` to list available lesson folders.

If the unit directory yields no results, stop with `❌ Unit "$UNIT" not found.`

Match LESSON to a folder name using this priority order:
1. Exact match (case-insensitive)
2. Prefix match (folder name starts with LESSON)
3. Substring match (folder name contains LESSON)

If multiple folders match at the same tier, list them and ask the user to choose. If nothing matches at any tier, stop with `❌ No lesson matching "$LESSON" found.` If you fuzzy-matched, show `⚠️  Resolved "$LESSON" → "$LESSON_SLUG"`.

Use `LESSON_SLUG` for all subsequent paths.

## Step 1: Check grounding

Read `generation/units/$UNIT/lessons/$LESSON_SLUG/lesson-state.json`. If `grounding != "complete"`, stop:
```
❌ Lesson not grounded. Run /lesson-ground $UNIT $LESSON_SLUG first.
```

If `lesson-plan.json` already exists in the lesson folder, show the user:
```
A video plan already exists for this lesson:
  <list the video names and their objectives>

Re-plan from scratch? [y/n]
```
If no: stop. If yes: proceed (the existing plan will be replaced).

## Step 2: Read source materials

Read all of the following:
- `generation/units/$UNIT/lessons/$LESSON_SLUG/source/objectives.md`
- `generation/units/$UNIT/lessons/$LESSON_SLUG/source/vocabulary.md`
- `generation/units/$UNIT/lessons/$LESSON_SLUG/source/slides_data.json`
- All `lesson_*_levels.json` files in the source folder

## Gotchas

- If `slides_data.json` is absent: skip slide-section mapping in the analysis and note in the plan output that slide data was unavailable. Do not stop.
- If no `lesson_*_levels.json` files exist: skip the levels-mapping section of the analysis guide and note it. Do not stop.
- Proceed with whatever source materials are available. A lesson with only objectives and vocabulary is enough to generate a plan.

## Step 3: Analyze

Read [analysis-guide.md](references/analysis-guide.md) for the full framework. Perform each section in order and show your reasoning explicitly before generating plans.

## Step 4: Generate plans

Always generate at least Plans A and B. Generate additional plans (C, D, …) for each meaningfully different grouping suggested by the coupling analysis.

- **Plan A — fully split:** one video per objective (or per tightly-coupled pair that cannot be separated). Maximum reuse; most videos.
- **Plan B — fully combined:** all objectives in one video. Note if estimated length exceeds 3 minutes.
- **Plan C, D, … — intermediate splits:** one plan per distinct grouping of objectives that the coupling analysis supports. For example, if objectives 1 and 3 are tightly coupled and 2 and 4 are tightly coupled, one plan might be [1,3] + [2,4]; another might be [1,3] + [2] + [4]. Generate at most 2 intermediate plans to avoid overwhelming the user.

Present each plan as a table:

```
Plan A — 4 videos
  Video                    Objectives                               Vocab
  ----------------------   ---------------------------------------- -----
  how-ai-thinks            Explain that AI models use probability… AI, probability
  patterns-in-data         Analyze patterns in AI responses…        (none)
  experimenting            Experiment with different prompts…       prompt
  refining-prompts         Refine AI-generated outputs…            abstraction
  Est. length: ~1.5 min / ~1 min / ~1.5 min / ~1 min

Plan B — 1 video
  talking-to-machines      All 4 objectives                         All vocab
  Est. length: ~5–6 min  ⚠️  Exceeds 3-minute limit

Plan C — 2 videos
  how-ai-thinks            Explain… / Analyze patterns…            AI, probability, abstraction
  prompting                Experiment… / Refine…                   prompt
  Est. length: ~2 min / ~2 min
```

After the tables, apply the recommendation criteria in two passes:

**Step 1 — Eliminate disqualified plans:**
- **Never exceed 3 minutes per video.** Any plan where a video's estimated scene count pushes past the 3-minute limit is eliminated. (Exception: if all plans are disqualified, flag it and recommend the least-bad option.)

**Step 2 — Rank remaining plans (apply in order):**
1. **Prefer independent videos.** A video focused on one objective (or one tightly-coupled cluster) is easier to reuse, update, and target. Split unless there is a concrete reason not to.
2. **Shorter is fine.** A 1-minute video is not a problem. Do not pad or combine objectives just to reach a minimum length.
3. **Keep prerequisites together.** If understanding objective B requires objective A, they belong in the same video even if other criteria would split them.
4. **Avoid mid-concept splits.** If two objectives share the same slide section and the same levels, splitting them would force the learner to context-switch mid-topic.

State which plan you recommend, note any eliminated plans, and cite the specific ranking criteria that drive the choice. If multiple plans score equally, recommend the one with more, shorter videos.

Ask:
```
Which plan? (A / B / C / D / … or describe a custom split)
```

## Step 5: Confirm video names

Once the user selects a plan, confirm the video names:
```
Using Plan C:
  1. how-ai-thinks
  2. prompts-and-patterns

Confirm these names, or suggest changes:
```

Video names should be lowercase-hyphenated slugs, descriptive but short (2–4 words).

## Step 6: Write lesson-plan.json

Write `generation/units/$UNIT/lessons/$LESSON_SLUG/lesson-plan.json`:

```json
{
  "unit": "$UNIT",
  "lesson": "$LESSON_SLUG",
  "videos": [
    {
      "name": "<video-slug>",
      "target_objectives": [
        "<full objective text>",
        ...
      ],
      "target_vocabulary": [
        "<vocab word>",
        ...
      ]
    },
    ...
  ]
}
```

`target_vocabulary` entries are the vocabulary *words* (e.g. `"probability"`, `"prompt"`), not definitions. Use the exact word strings from vocabulary.md.

## Step 7: Initialize video folders

```bash
python scripts/init_videos.py $UNIT $LESSON_SLUG
```

Print the script output directly.

## Step 8: Confirm

```
✅ Video plan initialized for "$LESSON_SLUG".

  Plan: <N> videos
  <list: video-name → N objectives>

  lesson-plan.json: generation/units/$UNIT/lessons/$LESSON_SLUG/lesson-plan.json
  Video folders:   generation/units/$UNIT/lessons/$LESSON_SLUG/videos/

Your videos are ready — do NOT run /video-init, the folders are already created.

Next: run /video-script for each video:
<list /video-script $UNIT $LESSON_SLUG <video-name> for each>
```
