# 05 — ADK Developer Experience: Standalone Video Generation

## Background

The system currently has two distinct user types that use different tools:

**Curriculum Architect** works in Claude Code. They set up the full file structure for a curriculum unit — running unit-init, lesson-init, lesson-ground, and lesson-plan to define which videos should be made, what modes they use, and what objectives they cover. Their work produces the authoritative file structure that the Developer inherits.

**Curriculum Developer** works in the ADK web agent. They generate specific videos one at a time. Today, the ADK agent only handles video generation (video-init through video-assemble) and assumes the Architect has already done all the setup. If no lesson structure exists, the agent stops.

The goal of this project is to make the ADK agent work well for the Developer without requiring the Architect to have prepared anything first.

---

## Problem

The ADK agent currently requires all of the following to exist before it can do anything useful:
- A grounded lesson folder (`lesson-state.json` with `grounding: complete`)
- Source materials in `source/`
- An initialized video folder with `script.json`

If any of these are missing, the agent tells the user to go run Claude Code skills first. This breaks the "come here and make a video" experience.

---

## Desired Developer Experience

The Developer opens the ADK agent and says: **"I want to make a video for aif1-v2-2025 lesson 2."**

The agent:
1. Checks whether lesson 2 is already grounded
2. If not: fetches lesson metadata from the Code.org API and grounds the source materials inline — no Claude Code prereqs required
3. Shows the user what the lesson covers (objectives, vocabulary, slide count)
4. Asks: "What kind of video do you want to make?" (concept / summary / re-teach / co-create)
5. Asks which objectives to cover and what to name the video
6. Creates the video folder and script.json
7. Continues with the full video pipeline (script → html → audio → assemble)

The Developer can also ask: **"What videos are set up and ready to generate?"** — the agent reads existing video folders, checks pipeline states, and lists what's been planned but not yet generated.

---

## Two Sub-cases for the Developer

### Inheriting the Architect's work
The lesson folder and lesson-plan.json already exist. The Developer picks a video from the plan and generates it. The agent reads the existing `script.json` (which already has `mode`, `brief`, `target_objectives` set by the Architect) and goes straight to video-script.

### Standalone generation
The Developer provides a unit+lesson directly. The agent creates the minimum structure needed, grounds the materials, walks through lightweight planning (mode + objectives), and generates the video. These videos persist to disk.

**Where standalone videos live:** Under `generation/units/standalone/lessons/` — the `standalone/` pseudo-unit already exists for this purpose. Videos made this way are organizational separate from Architect-prepared units but are not ephemeral; they persist exactly like any other video.

---

## What Needs to Be Built

### 1. ADK grounding tool (`backend/tools/ground_lesson.py`)

A new Python tool registered with the ADK agent. Takes `unit` and `lesson` (either a lesson slug or a lesson number). When called:

1. Checks if `generation/units/<unit>/lessons/<lesson>/lesson-state.json` exists with `grounding: complete` — if so, returns immediately (idempotent)
2. If the unit is a known Code.org unit: calls the Code.org API to fetch lesson metadata (title, objectives, vocabulary, resource URLs) and writes `sources.csv` — equivalent to unit-init + lesson-init but scoped to one lesson, without requiring `unit.json` to exist
3. Runs the equivalent of `ground-lesson.py` — fetches slides, levels, writes objectives.md and vocabulary.md
4. Returns `{status, lesson_slug, sources_fetched, errors}` for the agent to inspect

For the `standalone/` path: accepts a sources.csv supplied by the user (or built from a Google Slides URL they provide) instead of fetching from the Code.org API.

### 2. Updated `backend/agent.py`

- Add `ground_lesson` to the agent's tools list
- Load the `lesson-ground` and `lesson-plan`-adjacent skills if needed, OR handle lightweight planning inline via the updated `video-init` skill (which already captures mode + brief)
- Update the agent instruction to describe the new entry point:
  - If user provides a unit+lesson with no existing structure: call `ground_lesson`, then `load_lesson_sources`, then run `video-init`
  - If user provides a unit+lesson with existing structure: check pipeline state, list ready videos or proceed directly
  - Lightweight planning (mode, objectives, video name) happens via `video-init`, not `lesson-plan`

### 3. "List ready videos" capability

The agent should be able to answer "what's ready to generate?" by reading the lesson folder structure and summarizing pipeline states. This can be a simple `execute` call to list video folders and read each `script.json`'s `pipeline` field — no new tool needed, just instruction guidance.

---

## What Does NOT Change

- All Claude Code skills remain unchanged — the Architect's workflow is unaffected
- `lesson-plan` stays Claude Code only — the multi-video planning workflow with full coupling analysis is not needed in the ADK agent
- The file structure is identical whether the Architect or Developer created it — a Developer-created standalone video is indistinguishable on disk from an Architect-prepared one (except for its location under `standalone/`)
- The `video-init` skill (now with mode + brief) serves as the lightweight planning step for the ADK agent

---

## Deferred

The organizational rules for `standalone/` videos at production scale — ownership, promotion into a named unit, cleanup policies — are out of scope for this project and should be revisited before multi-developer production deployment.

---

## Files to Create or Modify

| File | Change |
|---|---|
| `backend/tools/ground_lesson.py` | New — Code.org API fetch + grounding for a single lesson |
| `backend/agent.py` | Add `ground_lesson` tool; update instruction for new entry point |
