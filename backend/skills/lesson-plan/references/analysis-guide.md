# Analysis Guide

Perform each section below in order and show your reasoning explicitly before generating plans.

## Map objectives to slide sections

Read the `notes` field of each slide in slides_data.json. Look for section markers (e.g. "Warm Up", "Activity", "Wrap Up") and topic headers. For each objective, identify which slides directly address it — cite the slide indices and notes text as evidence.

## Map objectives to levels

For each level in the levels JSON, read `longInstructions`. Identify which objective(s) each level is practicing. Note which objectives share the same levels.

## Identify coupling

Two or more objectives are **tightly coupled** if they:
- Map to the same slide section(s), AND
- Are practiced by the same levels, OR
- One is a prerequisite for understanding the other

Two objectives are **loosely coupled** (separate video candidates) if they:
- Map to different slide sections (e.g. one is in "AI Predictions", the other in "Prompting AI"), OR
- A student could struggle with one independently of the other

## Assign vocabulary

Map each vocab term to the video whose objectives it most directly supports. A term may appear in more than one video if it is relevant to multiple objectives.

## Estimate timing

For each proposed video, count the number of scenes it would likely need in re-teach mode. Re-teach mode synthesizes and condenses — expect roughly 1 scene per major concept or slide group, not 1 per slide. At ~10–15 seconds of narration per scene, the maximum is about 12 scenes (≈2.5–3 min). Shorter videos are fine and preferred. Flag any cluster whose scene count would push past 3 minutes.
