# Concept Mode Style Guide

Concept mode produces one scene per slide. It is the default teaching format — thorough, slide-by-slide narration that walks through the lesson in sequence.

## Structure requirements

- **Always start with an intro scene.** The first scene is a 1-2 sentence preview naming the key concepts the video will cover. Pair it with the first or title slide. This scene is always present regardless of slide count.
- **One scene per slide** after the intro. Do not combine or skip slides.
- **Complex slides may split into two scenes** if a single slide covers two genuinely distinct concepts that each require full explanation. Keep splits rare — default to one scene per slide.
- **Target scene length:** 15-25 seconds of spoken audio (roughly 50-85 words of speech). Scenes outside this range should be a deliberate choice, not an oversight.
- There is no required closing scene — end naturally with the last slide's content.

## Content rules

- Use the slide's speaker notes as the primary source for `speech`. Speaker notes represent the intended narration; treat them as close to authoritative.
- **When a slide has no speaker notes:** synthesize narration from the slide title and visible text content. Do not skip the slide. A slide with only a title still gets a scene — briefly name the concept and state its significance.
- **When speaker notes are thin (a few words):** expand them into complete narration. The notes are often a prompt for a live teacher, not a finished sentence — complete the thought.
- Cover every slide in order. Do not rearrange or consolidate.
- Vocabulary terms introduced on a slide should be named and defined in that scene's speech, consistent with `target_vocabulary`.

## Tone and language

- **Audience:** 9th grade students, assumed novice on this topic.
- **Register:** Clear and direct. Slightly warmer than a textbook but not overly casual — like a knowledgeable teacher talking through a slide, not reading it aloud.
- **Sentence structure:** Short to medium sentences. Avoid stacking multiple clauses. One idea per sentence is a useful default.
- **Vocabulary:** Use the lesson's vocabulary terms confidently once introduced. Plain language for everything else — avoid jargon not present in the source material.
- **Do not read the slide verbatim.** Paraphrase or expand — the viewer can already see the slide text.
- Avoid filler phrases: "Great!", "Now let's look at...", "As you can see..."

## `comment` field

The `comment` is a brief visual description used by the HTML generation step to design the slide. Write it as a visual brief, not a narration summary:

- Describe what should be *shown*, not what is *said*.
- Example: `"Title slide: 'What Is Machine Learning?' on a dark background"` — not `"Introduces the concept of machine learning"`.
- Keep it to one sentence.

## Gotchas

- A slide with only an image and no text still gets a scene. Describe the image's content in the comment and narrate what the image is meant to convey.
- Slides that are purely decorative transitions (e.g., a blank slide used as a section divider) may be skipped if they contain no teachable content — but this is rare.
- Do not invent content that isn't in the slides or speaker notes. If a concept is mentioned but not explained in the source, name it but do not fabricate an explanation.
