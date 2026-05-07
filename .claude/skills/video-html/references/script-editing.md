# Script Editing

Guidelines for evaluating the scene structure of a video script before HTML generation,
and for proposing optional edits. Loaded and applied during Mode D planning — after mode
selection, before the scene plan is built.

Two types of edits are in scope:
1. **Scene splits** - dividing one long-narration scene into two scenes with separate slides
2. **Speech text adjustments** - minor rewrites making abstract narration more visually concrete

Both require human approval before being applied.

---

## When to Consider a Scene Split

Split when ALL of these are true:
- The scene's `speech` contains two meaningfully distinct visual beats - a natural break
  where the slide content would change if given the opportunity
- Each resulting fragment is estimated at least 7 seconds
  (use: word count / 2.5 = estimated seconds at conversational educational pacing)
- The scene is not already brief (do not split scenes estimated under 14 seconds total)
- AUDIO_LOCKED is false

Do NOT split when:
- Either fragment would be under 7 seconds (see exception below)
- The narration is one tight continuous thought
- The scene is structured as a list where all items belong on one slide
- The scene introduces a vocabulary term AND the split would separate the term from its
  definitional sentence — elaboration and examples that follow an established definition
  may go on a separate slide

**Exception — standalone key insight:** If the narration contains a single, self-contained
insight sentence that would land with high impact on its own slide, it may anchor its own
scene even if the resulting fragment is under 7 seconds. When proposing this split in the
scene plan, flag the short scene with a visually direct template recommendation
(`big-quote`, or `header-with-image` using AI gen) so the impact is immediate — the viewer
should be able to hear and absorb the statement before the next scene begins.

Flag scenes estimated at 20+ seconds as split candidates. Scenes at 14-19 seconds
may be worth splitting only if two very distinct visual beats exist.

---

## When to Consider a Speech Text Adjustment

Propose a speech adjustment only when the current text would produce a genuinely
poor or uninterpretable image prompt, AND a text-based or SVG template can't
serve the scene better.

In scope:
- Making an abstract sentence more visually concrete for image generation
- Replacing a vague spatial description with a grounded, depictable one

Out of scope - do NOT propose:
- Adding new concepts or examples not in the original
- Removing any content
- Reordering sentences
- Changing meaning, emphasis, or tone

---

## Evaluation Process

After reading the full script, assess each scene. Scenes with no issues need no mention.

If no scenes have issues, print:
> No script edits needed - proceeding to planning.

And continue to SKILL.md Step 4 (Load Planning Context).

---

## Approval Format

If any edits are proposed, present them all at once before touching script.json:

```
## Proposed Script Edits

[N] proposed edit(s). Review and approve or decline.

---

### Edit 1 - Scene [X]: Split into 2 scenes

**Reason:** [one sentence on why the split improves the visual]

BEFORE (1 scene):
  Comment: [original comment]
  Speech:  "[full original speech text]"

AFTER (2 scenes):
  Scene [X]a:
    Comment: [new comment]
    Speech:  "[first portion]"

  Scene [X]b:
    Comment: [new comment]
    Speech:  "[second portion]"

---

### Edit 2 - Scene [Y]: Speech adjustment

**Reason:** [one sentence on what the change enables visually]

BEFORE:
  Speech: "[original]"

AFTER:
  Speech: "[full scene speech with change in context]"

---

Approve all edits? Or specify which to accept / decline / modify.
```

Wait for user response before writing anything to script.json.

---

## Applying Approved Edits to script.json

**Splits:** Replace the original scene with two new scene objects, each containing
only `comment` and `speech`. Do not carry over `elevenlabs`, `gemini`, `duration`,
or `audio` - those are added by later skills. Scene count increases by 1 per split.

**Speech adjustments:** Update only the `speech` field of the affected scene.
Do not touch `elevenlabs` or `gemini` (they don't exist yet at this pipeline stage).

Write the updated `scenes` array back to script.json, leaving all other fields intact.

Print confirmation:
> Script updated: [N] split(s) applied, [N] speech adjustment(s) applied. [X] total scenes.
> Proceeding to Step 4 (Load Planning Context).

---

## Hard Limits

- Never add content not in the original speech
- Never remove content from the original speech
- Never reorder scenes
- If AUDIO_LOCKED is true, skip this entire file and return immediately
