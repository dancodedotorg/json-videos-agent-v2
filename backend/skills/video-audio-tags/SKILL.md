---
name: video-audio-tags
description: Enhances the voiceover script with expression tags for both ElevenLabs and Gemini TTS. Produces both elevenlabs and gemini fields in one pass. Includes human check-in for approval.
---

# video-audio-tags

Add expression tags to the voiceover script for a video.

## Path detection

Extract UNIT, LESSON, and VIDEO from the user's message, or from session context if continuing from a previous step. Only ask if genuinely unknown.

Use `execute` to list `generation/units/$UNIT/lessons/` and match LESSON to the closest folder name as LESSON_SLUG. If the unit directory doesn't exist, stop with `❌ Unit "$UNIT" not found.` If nothing matches, stop with `❌ No lesson matching "$LESSON" found.` If you fuzzy-matched, show `⚠️  Resolved "$LESSON" → "$LESSON_SLUG"`.

- Script path: `generation/units/$UNIT/lessons/$LESSON_SLUG/videos/$VIDEO/script.json`

All steps below use SCRIPT_PATH derived above.

## Prerequisites

- `pipeline.html` must be `"complete"` in `script.json`

## Gotchas

- **ElevenLabs pause tags are disabled**: Do NOT use `[short pause]`, `[long pause]`, or any pause tag in ElevenLabs output. The player inserts silence at scene boundaries automatically. The ElevenLabs reference guide lists these as valid — they are not valid here.
- **Do not modify speech text**: The ElevenLabs reference guide (Step 4 of its workflow) suggests adding emphasis via capitalization, punctuation changes, and ellipses. Do NOT do this. Speech text is fixed; only add bracketed tags around it.
- **Non-verbal tags in educational content**: ElevenLabs supports non-verbal sounds like `[sighs]`, `[chuckles]`, `[laughing]`. Use these only when they reflect a genuinely natural vocal moment (e.g., a light `[chuckles]` before a joke). Do not use them as generic filler or to simulate personality.

## Step 1: Read Script

Read SCRIPT_PATH. Extract only the `scenes[].speech` fields — do not read HTML or any base64 content.

## Step 2: Add Expression Tags

Before generating any tags, use `load_skill_resource` to read both reference files:
- `references/elevenlabs-tts-prompting-guide.md`
- `references/gemini-tts-prompting-guide.md`

For each scene's `speech`, produce **both** an `elevenlabs` version and a `gemini` version. The two providers use different tag systems — apply each independently.

---

### ElevenLabs Tags

ElevenLabs voices have a neutral, flat default delivery — tags are the primary lever for expressiveness.

**Rules**:
- Only add tags where they genuinely improve delivery — don't over-tag
- Tags may appear at the start of a scene to set overall tone, or inline before a specific phrase to mark a tonal shift
- Keep the actual speech text unchanged — only add tags, do not reword or alter punctuation
- Each scene should have 1–2 tags maximum

> For the full tag list, recommended educational tags, and examples, see the elevenlabs-tts-prompting-guide.md already loaded above.

---

### Gemini Tags

Gemini TTS uses a richer, more expressive tag set. Tags can appear at the start of a scene or inline to change delivery of specific phrases.

> For the full tag list and advanced prompting strategies, see the gemini-tts-prompting-guide.md already loaded above.

**Recommended tags for educational content**:
- `[warmly]` — friendly, inviting tone
- `[clearly]` — articulate, precise delivery
- `[deliberately]` — measured, intentional pacing
- `[curious]` — inquisitive, exploratory
- `[seriously]` — focused, important point
- `[amazed]` — genuine surprise or delight
- `[excitedly]` — high energy, enthusiasm
- `[thoughtfully]` — reflective, deeper concept

**Rules**:
- Tags may appear at the start of a scene for overall tone, or inline before a specific phrase to mark a tonal shift
- Keep the actual speech text unchanged — only add tags, do not reword
- 1–3 tags per scene maximum
- Gemini can handle more nuanced tags than ElevenLabs — prefer descriptive adverbs (`[warmly]`, `[deliberately]`) over simple emotions
- The Gemini persona already sets a warm, clear, moderate baseline — use tags to *deviate* from that baseline (excitement for reveals, deliberateness for definitions, seriousness for key distinctions). Tags that just reinforce the default tone add little value.

**Example**:
- Speech: `"Today we're going to learn about functions. Functions are one of the most powerful tools in programming."`
- Gemini: `"[excitedly] Today we're going to learn about functions. Functions are one of the most powerful tools in programming."`

---

## Step 3: Write to script.json

Read SCRIPT_PATH, add both `elevenlabs` and `gemini` fields to each scene (keeping all existing fields), set `pipeline.audio_tags = "complete"`, write it back.

## Step 4: Human Check-In

Show the user the before/after for each scene in a compact format:
```
Scene 1:
  speech:     "..."
  elevenlabs: "..."
  gemini:     "..."
```

Then ask:
> Do the audio tags look right? You can ask me to adjust specific scenes, the overall energy level, or tags for a specific provider. Or say "looks good" to move on.

Iterate on any requested changes. Then tell the user:
Ask: "Ready to generate the audio? Say yes to continue — I'll ask you to pick a voice provider first."
