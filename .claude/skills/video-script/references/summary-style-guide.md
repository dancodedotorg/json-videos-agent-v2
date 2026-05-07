# Summary Mode Style Guide

Summary mode produces a compact overview of the lesson — fewer scenes, grouped thematically, each synthesizing multiple slides into a single key takeaway. Use when the goal is review or orientation, not detailed instruction.

## Structure requirements

- **Always start with an intro scene.** The first scene is 1-2 sentences orienting the viewer: what topic this video covers and what they'll walk away knowing. Pair it with the title or first slide.
- **3-8 scenes total** (including the intro). Fewer than 3 scenes is too sparse; more than 8 defeats the purpose of summarizing.
- **Group slides thematically**, not just sequentially. Slides that share a common concept, question, or activity belong in one scene even if they're not adjacent in the deck.
- There is no required closing scene, but a brief wrap-up scene ("The main idea is...") can be added when the lesson has a clear single takeaway worth reinforcing.

## Grouping criteria

Group slides together when they:
- Explain different aspects of the same concept (e.g., multiple slides building a definition)
- Walk through steps of the same procedure
- Present examples of the same idea
- Form a conceptual unit that the lesson treats as one topic

Do not group slides just because they're sequential. A new group starts when the conceptual focus shifts — even mid-sequence.

**Practical check:** if you removed one slide from the group, would the scene's speech still make sense? If yes, the grouping is probably correct. If no, you may need to break it into two scenes.

## What is a "key takeaway"?

A key takeaway is the insight a student should carry away from a group of slides — not a list of details, but the one thing that makes the rest make sense.

- "The model learns from examples, not rules" — takeaway
- "The model uses a training dataset and an algorithm and an objective function..." — not a takeaway

For each scene, ask: if a student forgot everything else from this video, what is the one sentence I want them to remember? That's the scene's `speech` anchor.

## Content rules

- Each scene synthesizes its slides into 1-3 sentences of speech. Scenes are shorter than concept mode.
- Target scene length: 10-20 seconds (roughly 35-65 words of speech). Intro and closing scenes may be slightly shorter.
- Skip slides that are purely procedural scaffolding (navigation instructions, "click here" steps) unless the procedure itself is a key takeaway.
- Do not skip entire conceptual sections. Every major topic in the lesson should have representation, even if abbreviated.
- Vocabulary terms in `target_vocabulary` must appear in the summary — at minimum, each term is named and given a one-phrase definition.

## Tone and language

- **Audience:** 9th grade students who have already completed (or are about to complete) the lesson.
- **Register:** Confident and efficient. This is a review, not a first introduction — the viewer has some context. Slightly faster-paced than concept mode.
- **Sentence structure:** Short sentences, active voice. The goal is clarity at speed.
- **Do not narrate slide by slide.** Never say "on slide 3" or "the next slide shows." Speak at the level of ideas, not slides.
- Avoid: "In this video we will cover...", "Let's take a look at...", transition filler.

## `comment` field

Same convention as concept mode — describe what should be visually shown, not what is said:
- For grouped slides, reference the dominant visual theme of the group, or suggest a synthesized visual that captures the group's concept.
- Example: `"Diagram showing inputs flowing into a model and outputs flowing out"` rather than `"Covers slides 4-6 about model input/output"`.

## Gotchas

- Summary mode is frequently confused with concept mode when the slide deck is small (< 6 slides). If the source has few slides, summary mode may produce scenes that are too short to be meaningful. Consider alerting the user and asking if they still want summary mode, or default to concept mode groupings.
- Do not summarize the intro scene — it is already a summary. The intro should name the topic and promise, not recap slide 1.
- If `target_objectives` is set, use it to decide which sections of the lesson receive more emphasis. Sections not addressed by any target objective can be compressed most aggressively.
