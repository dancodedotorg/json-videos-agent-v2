# Re-teach Style Guide

A re-teach video is a short remediation video for students who completed the lesson but need reinforcement. It does not replace the lesson — it re-explains the same concepts more explicitly, using the same vocabulary and examples the lesson used.

---

## Structure

**Always start with an intro scene.** The first scene in every re-teach video is a short title-slide scene: 1-2 sentences that name the key concepts or questions the video will cover. Nothing more. This scene is paired with a simple title slide visual in the HTML step.

**Follow the lesson's own structure.** Scenes should progress in the same order as the lesson content. Do not reorder concepts or introduce your own arc.

**Target length: 2-3 minutes.** Let the target objectives determine the natural scene count. At roughly 15-20 seconds of narration per scene, this is typically 8-12 scenes. Flag if the content scope would push beyond 3 minutes.

**End with a Question of the Day scene (when relevant).** Check the source slides for a "Question of the Day." If the question connects directly to this video's target objectives, the final scene should return to it — use it as a prompt to synthesize what was just covered. If the QotD spans the whole lesson and is more relevant to another video in the lesson, omit it.

---

## Content Rules

**Explain more explicitly than the lesson did.** The lesson introduced concepts quickly; the re-teach video slows down and makes the reasoning visible. More direct statements, fewer implied connections.

**Walk through student activities.** When the lesson included a Level activity, describe what students did and what a strong response or observation looks like. Don't just name the activity — explain what the takeaway should have been.

**Do not introduce new analogies or metaphors.** Only use examples and comparisons that were already in the source material. You may extend or elaborate on them, but not replace them.

**Elaboration pass.** After drafting scenes, apply a deliberate elaboration pass. Add one or two follow-up sentences to a scene when any of these are true:
- The concept is the hardest to intuitively grasp in this video
- The "so what" is not obvious from the definition alone
- There is a common misconception worth explicitly correcting
- The concept is central to the target objectives

Scenes that are framing (intro, summary, QotD close) or self-evident should stay lean. Do not elaborate every scene.

---

## Referencing the Lesson

**Only reference student-facing actions.** When connecting back to the lesson, refer to things students did: warm-up activities, class discussions, specific level tasks. Use language like "In the warm-up, you...", "In Level 1, you...", "During the discussion, you saw..."

**Never reference teacher actions.** Do not say things like "your teacher explained," "the teacher showed you," or "as your teacher described." The student is watching this video independently — teacher-directed framing breaks that context.

---

## Tone and Language

**Audience:** 9th grade students, novice level. Assume no prior knowledge of the concepts.

**Register:** Casual and direct. Write the way a knowledgeable peer would explain something, not the way a textbook would.

**Sentence structure:** Short, clear sentences. Avoid stacking multiple clauses. If a sentence needs a comma to hold two ideas together, consider splitting it.

**Academic vocabulary:** Use lesson vocabulary terms confidently and accurately — these are words students are expected to learn (e.g. "probability," "abstraction," "prompt"). Do not avoid them or over-define them every time they appear. For everything else, prefer plain language.

**Avoid:** Overly formal phrasing, passive voice, and multi-clause elaborations that obscure the point.

---

## comment field

The `comment` is a visual brief for the HTML generation step. Write it as a description of what should be *shown*, not a summary of what is *said*.

- For concept explanation scenes: suggest a simplified or annotated version of the original slide visual — something that makes the concept clearer than the original, not a reproduction of it.
- For activity walk-through scenes: suggest a visual that evokes what students did (e.g., `"Screenshot-style view of an AI chat interface with a sample prompt filled in"`) rather than what a teacher showed.
- For the intro scene: a clean title card framing the re-teach purpose (e.g., `"Title slide: 'Let's Revisit: What Is a Model?' with a subtle 'reinforcement' visual cue"`).
- For the Question of the Day scene: a visual that presents the question prominently so the student can sit with it.
- Keep it to one sentence.

---

## Gotchas

- **Don't reference original lesson slide numbers or visual design.** The student is watching independently — they don't have the original slides in front of them.
- **If a Level's content isn't in the source materials:** describe the type of activity and its purpose without inventing specific details from the level. For example: "In the chat activity, you experimented with prompting an AI model..." is fine even without the exact level content.
- **The intro scene is not a copy of the lesson's opening slide.** It should orient to this video's re-teach purpose and name the specific concepts being revisited — not replay how the lesson started.
- **If target objectives require covering a concept that has no corresponding source content:** flag this to the user before generating. Do not invent content to fill the gap.
