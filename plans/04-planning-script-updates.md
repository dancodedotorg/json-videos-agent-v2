# Plan: Move mode + brief from video-script to lesson-plan / video-init

## Context

The `video-script` skill currently asks the user to choose a generation mode (concept / summary / re-teach / co-create) at Step 2, before any script generation begins. This is a planning decision — it determines the *purpose and structure* of the video — not a scripting decision. It belongs alongside the other planning decisions (which videos to make, which objectives each covers) that live in `lesson-plan` and `video-init`.

The fix: capture `mode` and `brief` at plan/init time, store them in `lesson-plan.json` → `script.json`, and have `video-script` read them from `script.json` instead of asking interactively. This also unifies co-create: instead of special-casing the brief, every video has a `brief` field — null for predefined modes (the reference doc is the brief), populated for co-create.

---

## Files to change

| File | Change |
|---|---|
| `.agents/skills/lesson-plan/SKILL.md` | Ask mode first; make coupling analysis conditional on re-teach; update schema |
| `.agents/skills/lesson-plan/scripts/init_videos.py` | Write `mode` and `brief` into script.json |
| `.agents/skills/video-init/SKILL.md` | Add mode+brief selection step; load mode-guide.md; update script.json template |
| `.agents/skills/video-script/SKILL.md` | Remove Step 2 (mode selection); read mode+brief from script.json |
| `.agents/skills/video-script/references/mode-guide.md` | **New file** — canonical mode descriptions + brief requirements |

`video-create/SKILL.md` needs no changes.

---

## Change 1: `lesson-plan/SKILL.md`

The flow is restructured so **mode is asked before the split analysis**, because mode determines whether the analysis is needed at all. The coupling analysis (Plan A/B/C) is conditional on re-teach being in the mix.

### New lesson-plan flow

**Step 2 (new): Ask what types of videos the user wants**

Before reading source materials or doing any analysis, ask:

> ```
> What type of video(s) do you want to make for this lesson?
>
>   concept   — one scene per slide; thorough tutorial narration
>   summary   — 3–8 scenes, thematic grouping; best for review/overview
>   re-teach  — remediation for students who completed the lesson
>     ↳ If you choose re-teach, I'll analyze the lesson objectives next
>       and recommend how many re-teach videos to make.
>   co-create — you provide a custom brief (audience, angle, tone, length)
>
> You can mix types (e.g., "one concept and some re-teach videos").
> What type(s) do you want?
> ```

Wait for the user's response. **Do not ask "how many" for re-teach** — count is determined by the upcoming coupling analysis, not the user upfront. For concept/summary, default to one per lesson unless the user specifies otherwise. For co-create, collect the brief now (thin-brief validation: one follow-up question for the most important gap, never more than one). Store the requested types.

**Step 3 (new): Read source materials** — same as current Step 2 (read objectives, vocabulary, slides_data.json, levels JSON).

**Step 4 (conditional): Coupling analysis and plan generation**

Run the full analysis (current Steps 3–4, using `analysis-guide.md`) **only if**:
- Any requested video is re-teach, OR
- The user requested multiple videos and needs help grouping content

For concept, summary, or single co-create requests: **skip this step entirely**. Proceed directly to video naming.

When the analysis IS run, present split plans as today. Objective and vocabulary assignments are most meaningful for re-teach. For concept/summary videos in a multi-video set, split by natural slide sections rather than objective coupling.

**Step 5: Confirm video names** — same as today.

**Step 6: Write lesson-plan.json** — schema updated (see below). No separate mode-selection step needed because mode was captured in Step 2.

**Step 7: Initialize video folders** — same as today (`init_videos.py`).

**Step 8: Confirm** — same as today.

### Updated lesson-plan.json schema (Step 6)

```json
{
  "unit": "$UNIT",
  "lesson": "$LESSON_SLUG",
  "videos": [
    {
      "name": "<video-slug>",
      "target_objectives": ["<full objective text>", "..."],
      "target_vocabulary": ["<vocab word>", "..."],
      "mode": "concept",
      "brief": null
    }
  ]
}
```

Note: `brief` is a string for co-create, `null` for all other modes.

---

## Change 2: `init_videos.py`

In `create_video()`, read `mode` and `brief` from the video plan entry and write them into `script.json`.

**Current** (lines 80–87):
```python
script = {
    "video_name": name,
    "unit": unit,
    "lesson": lesson,
    "target_objectives": video.get("target_objectives", []),
    "target_vocabulary": video.get("target_vocabulary", []),
    **SCRIPT_TEMPLATE,
}
```

**New**:
```python
script = {
    "video_name": name,
    "unit": unit,
    "lesson": lesson,
    "target_objectives": video.get("target_objectives", []),
    "target_vocabulary": video.get("target_vocabulary", []),
    "mode": video.get("mode", "concept"),
    "brief": video.get("brief", None),
    **SCRIPT_TEMPLATE,
}
```

No other changes to the script.

---

## Change 3: New shared reference doc — `mode-guide.md`

Create `.agents/skills/video-script/references/mode-guide.md` (or a shared location accessible to both lesson-plan and video-init). This doc is the canonical description of modes and brief requirements. Both lesson-plan and video-init load it instead of duplicating the prose.

Content:
- Mode descriptions (concept / summary / re-teach / co-create)
- What a complete co-create brief contains (audience, angle, tone, length)
- Thin-brief handling: one follow-up question, pick the biggest ambiguity, never ask multiple

Both skills reference this doc when presenting mode choices. The *questions* still appear in each skill (they serve different contexts), but the definitions and brief validation rules are canonical here.

## Change 4: `video-init/SKILL.md`

`video-init` is the standalone single-video path (bypasses `lesson-plan`). It captures mode and brief for ONE video.

**Insert a new Step 3 between Step 2 "Load objectives" and Step 3 "Write script.json".** Renumber Step 3 → Step 4, Step 5 stays Step 5.

New Step 3 content:

> Use `load_skill_resource` to read `references/mode-guide.md`. Then ask:
>
> ```
> How should this video be generated?
> (concept / summary / re-teach / co-create)
> ```
>
> Wait for the user's response. If co-create, collect the brief per mode-guide.md rules.
> Store MODE and BRIEF. BRIEF is null for non-co-create modes.

**Update Step 4 script.json template** to include `mode` and `brief`:

```json
{
  "video_name": "$VIDEO",
  "unit": "$UNIT",
  "lesson": "$LESSON",
  "target_objectives": [<TARGET_OBJECTIVES>],
  "target_vocabulary": [<TARGET_VOCABULARY>],
  "mode": "<MODE>",
  "brief": <BRIEF or null>,
  "width": 1600,
  "height": 900,
  "pipeline": { ... },
  "grounding": {},
  "tts": {},
  "scenes": []
}
```

---

## Change 4: `video-script/SKILL.md`

**Step 1 — Read script.json metadata:** Expand extraction to include `mode` and `brief`:
> Extract: `target_objectives`, `mode`, `brief`. Confirm `pipeline.grounding == "complete"`.

**Step 2 — Delete entirely.** The mode selection prompt and wait-for-response logic is removed. No user interaction happens here anymore.

**Renumber:** Steps 3–7 become Steps 2–6.

**New Step 4 (was Step 5) — Generate Scenes:** Replace the opening paragraph with:

> Before generating, use `load_skill_resource` to read the style guide for the mode stored in `script.json`:
>
> - **concept**: load `references/concept-style-guide.md`
> - **summary**: load `references/summary-style-guide.md`
> - **re-teach**: load `references/reteach-style-guide.md`
> - **co-create**: load `references/co-create-style-guide.md`
>
> For **co-create**, also read the `brief` field from `script.json`. Use the style guide for structural rules and scene guardrails; use `brief` for creative direction (audience, angle, tone, length). If `brief` is null for a co-create video, apply the defaults from the co-create style guide.
>
> For **all modes**, if `brief` is non-null (even for predefined modes), incorporate it as supplemental guidance alongside the reference doc.

The rest of the Generate Scenes step (the scene object schema, etc.) is unchanged.

---

## Verification

End-to-end test path (read-only check before running):
1. Run `/lesson-plan` on a grounded lesson → confirm plan output now includes mode selection step and `lesson-plan.json` has `mode` + `brief` fields per video
2. Confirm `init_videos.py` writes `mode` and `brief` into each `script.json`
3. Run `/video-script` → confirm it skips mode selection, reads `mode` from `script.json`, and loads the correct style guide without prompting
4. Run `/video-init` for a standalone video → confirm mode + brief are captured and written to `script.json`
5. For a co-create video: confirm brief is captured at plan/init time and used (not re-asked) by `video-script`
