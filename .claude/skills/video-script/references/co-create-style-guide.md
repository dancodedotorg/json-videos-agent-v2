# Co-Create Mode Style Guide

Co-create mode generates a script from a user-provided brief rather than following a fixed structure. It offers the most creative latitude of any mode — the user defines the angle, audience, or focus, and the script is shaped around that intent.

## What a complete brief contains

A good brief specifies:
- **Audience** — who is watching and what they already know (e.g., "students who just finished the lesson", "parents with no CS background")
- **Angle or focus** — what aspect of the lesson to center on (e.g., "focus only on the vocabulary terms", "show how this connects to everyday life")
- **Tone override** — if different from the default casual-direct register (e.g., "more conversational", "formal academic")
- **Target length** — approximate number of scenes or minutes (e.g., "keep it under 2 minutes", "around 5 scenes")

## What to do when the brief is thin

If the user's brief is one sentence or lacks key dimensions, ask one follow-up question to resolve the most important gap before generating. Do not ask multiple questions — pick the single biggest ambiguity.

If the user asks you to proceed despite a thin brief, apply these defaults:
- **Audience:** same as re-teach mode (9th grade students, novice level, just completed the lesson)
- **Angle:** highlight what the target objectives say students should be able to do, framed in plain language
- **Tone:** casual and direct, same as re-teach
- **Length:** 4-7 scenes

## Scene structure

Co-create has no fixed scene structure — scene count and ordering should serve the brief. However:
- **Start with a grounding scene** unless the brief explicitly asks otherwise. Even a brief focused on a single angle benefits from 1 sentence of context so the viewer knows what they're watching.
- **End with a clear landing** — the final scene should resolve or conclude, not just stop. A one-sentence wrap-up ("So next time you...") is usually enough.

## Content rules

- Stay grounded in the source material. Co-create is not a license to fabricate content not present in the lesson. The brief shapes the angle and emphasis, not the facts.
- Honor the brief over the source structure. If the brief asks to focus on a single concept, it is correct to omit other lesson content entirely.
- `target_vocabulary` terms should still appear if the brief's angle touches them — but they are no longer required if the angle bypasses them.
- If the brief asks for a narrative device (e.g., "frame it as a story", "use questions and answers"), apply it consistently across all scenes.

## Tone and language

- Default to the brief's specified tone. If none is specified, use the re-teach defaults: 9th grade audience, casual and direct register, short sentences.
- Respect explicit tone overrides completely — if the user asks for a formal tone, do not drift back to casual.
- If the brief specifies an unusual audience (e.g., teachers, parents), adjust vocabulary and framing accordingly without being asked.

## `comment` field

The comment should describe visuals that serve the brief's angle, not just the slide content:
- If the brief asks for a "real-world connection" angle, the comment should suggest a real-world visual rather than a slide diagram.
- If the brief asks for a specific tone or narrative device, hint at it in the comment (e.g., `"Split screen: question on left, answer revealed on right"`).

## Gotchas

- Co-create often produces scripts that don't map one-to-one to slides. The HTML generation step will need more creative latitude as a result — note this in the script's comments so downstream steps are prepared.
- If the brief contradicts the `target_objectives` (e.g., the brief focuses on something the video was not planned to cover), flag the conflict to the user before generating. They may want to reconsider the brief or update the objectives.
- Do not silently expand the scope of the brief. If the user asks for "a 2-minute video about vocabulary", produce that — do not add extra scenes covering other lesson content without asking.
