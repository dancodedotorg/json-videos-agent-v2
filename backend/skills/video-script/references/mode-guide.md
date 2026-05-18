# Video Generation Mode Guide

Every video has a **mode** that determines how the script is structured and what the video is for. Mode is chosen at planning time (in `/lesson-plan` or `/video-init`) and stored in `script.json`. The script generation step reads mode from `script.json` — it does not ask for it interactively.

## Modes

### concept
One scene per slide. Thorough tutorial narration that walks through the lesson in sequence.
- Best for: first-exposure teaching videos, full lesson walkthroughs
- Scene count: one per slide (plus required intro)
- Style guide: `concept-style-guide.md`

### summary
3–8 scenes covering key takeaways, grouped thematically. Synthesizes multiple slides into one idea per scene.
- Best for: review or orientation before/after a lesson
- Scene count: 3–8 (including intro)
- Style guide: `summary-style-guide.md`

### re-teach
Remediation for students who completed the lesson but need reinforcement. Follows the lesson's own structure, explains more explicitly, and walks through student activities.
- Best for: students who completed the lesson and need another pass
- Scene count: typically 8–12 scenes (~2–3 minutes)
- Style guide: `reteach-style-guide.md`

### co-create
Custom brief provided by the user. The script is shaped around the brief's specified audience, angle, tone, and length — not a fixed structure.
- Best for: non-standard use cases (parent explainers, teacher prep, vocabulary focus, etc.)
- Scene count: determined by the brief (default 4–7 if not specified)
- Style guide: `co-create-style-guide.md` (structural rules) + `brief` field in script.json (creative direction)

---

## The `brief` field

Every video in `lesson-plan.json` and `script.json` has a `brief` field:
- For **concept / summary / re-teach**: `brief` is `null` by default. The mode's reference doc is the brief. If `brief` is non-null, treat it as supplemental guidance that customizes the reference doc behavior (e.g., "emphasize vocabulary over slide narration").
- For **co-create**: `brief` is required. It is the primary creative direction for the script.

### What a complete co-create brief contains

A good brief specifies:
- **Audience** — who is watching and what they already know (e.g., "students who just finished the lesson", "parents with no CS background")
- **Angle or focus** — what aspect of the lesson to center on (e.g., "focus only on the vocabulary terms", "show how this connects to everyday life")
- **Tone override** — if different from the default casual-direct register (e.g., "more conversational", "formal academic")
- **Target length** — approximate number of scenes or minutes (e.g., "keep it under 2 minutes", "around 5 scenes")

### Thin brief handling

If the user's co-create brief is one sentence or lacks key dimensions, ask **one** follow-up question to resolve the most important gap. Do not ask multiple questions — pick the single biggest ambiguity. If the user asks you to proceed despite a thin brief, apply these defaults:
- **Audience:** 9th grade students, novice level, just completed the lesson
- **Angle:** highlight what the target objectives say students should be able to do, framed in plain language
- **Tone:** casual and direct
- **Length:** 4–7 scenes
