---
name: video-audio
description: Generates TTS audio (MP3) and calculates per-scene durations for a video project. Asks the user to confirm provider and voice before running. Invoke with /video-audio <unit-slug> <lesson-slug> <video-name>.
compatibility: Requires Python 3.10+, elevenlabs, google-genai, pydub packages, and API keys in generation/tools/.env
allowed-tools: Read Write Bash(python *)
metadata:
  disable-model-invocation: "true"
  argument-hint: "<unit-slug> <lesson-slug> <video-name>"
---

# video-audio

Generate audio and scene durations for a video.

## Path detection

Parse `$ARGUMENTS` (3 words): UNIT=first, LESSON=second, VIDEO=third

List `generation/units/$UNIT/lessons/` and match LESSON to the closest folder name as LESSON_SLUG. If the unit directory doesn't exist, stop with `❌ Unit "$UNIT" not found.` If nothing matches, stop with `❌ No lesson matching "$LESSON" found.` If you fuzzy-matched, show `⚠️  Resolved "$LESSON" → "$LESSON_SLUG"`.

- Script path: `generation/units/$UNIT/lessons/$LESSON_SLUG/videos/$VIDEO/script.json`

All steps below use SCRIPT_PATH derived above.

## Prerequisites

- `pipeline.audio_tags` must be `"complete"` in `script.json`
- For ElevenLabs: `ELEVENLABS_API_KEY` in `generation/tools/.env`
- For Gemini: `GOOGLE_API_KEY` in `generation/tools/.env`

## Step 1: Human Check-In (ask before running)

Read `references/providers.md` for current provider and voice options, then present the full menu inline and ask the user to choose:

> **Which provider and voice?**
>
> **ElevenLabs** — Dan (warm, neutral American) · Sam (calm, professional) · Adam (deep, authoritative) · Hope (bright, friendly)
> **Gemini** — Zephyr (bright, upbeat) · Puck (upbeat, energetic) · Aoede (warm, expressive) · Kore (firm, clear) · Fenrir (grounded, measured)
> **Fake** — no audio, 3s per scene
>
> Default: ElevenLabs + Dan

Wait for the user's answer before proceeding.

## Step 2: Run Audio Generation

Run exactly one of these commands. Do not modify the command or add flags.

**ElevenLabs:**
```bash
python .claude/skills/video-audio/scripts/elevenlabs-gen.py $SCRIPT_PATH --voice <VOICE>
```

**Gemini:**
```bash
python .claude/skills/video-audio/scripts/gemini-audio-gen.py $SCRIPT_PATH --voice <VOICE>
```

**Fake:**
```bash
python .claude/skills/video-audio/scripts/elevenlabs-gen.py $SCRIPT_PATH --fake
```

The scripts write all `tts.*` fields and `pipeline.audio = "complete"` to `script.json` automatically. No manual JSON edits are needed after the script exits.

### Generation modes (for reference)

| Provider | Mode | Audio files | Duration source |
|---|---|---|---|
| ElevenLabs | combined | `audio/voiceover.mp3` | character-level alignment |
| Gemini | per_scene | `audio/scene_01.mp3`, … | measured from each MP3 |
| Fake | fake | none | 3.0s per scene |

## Step 3: Report and Continue

Tell the user:
- Provider and voice used
- How many scenes were processed
- Total duration (sum of all `scenes[].duration` values in `script.json`)
- Which generation mode was used
- For Gemini: how many individual MP3 files were created

Then tell them the next step:
- "Run /video-assemble $UNIT $LESSON $VIDEO to assemble the final player-ready script."

## Gotchas

- **0.5s pad on every duration** — both scripts add `+ 0.5s` to the measured audio length when setting `scenes[].duration`. This is intentional breathing room. If durations look longer than the audio, that is why.
- **ElevenLabs `[pause]` separator is not in alignment data** — the `eleven_v3` model converts `[pause]` markers to silence and omits those characters from its alignment output. The cursor does NOT advance for separator text. The duration math depends on this behavior — if the model changes, alignment will drift.
- **Missing `audio_tags` → silent scenes in Gemini** — if `pipeline.audio_tags` is not `"complete"`, scenes may have empty `gemini` fields. Gemini will skip those scenes (duration = 0s) without erroring. Always verify tags are complete before running.
