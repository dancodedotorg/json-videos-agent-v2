# TTS Providers and Voices

Reference for Step 1 of `/video-audio`. Read this file, then ask the user to choose a provider and voice.

---

## Providers

### ElevenLabs

Real audio generation using character-level alignment. Always runs in **combined** mode: all scenes are joined into one API call and the result is saved as `audio/voiceover.mp3`. Durations are calculated from ElevenLabs character alignment data.

**Cost:** ElevenLabs credits per character.
**Best when:** High quality, natural-sounding voices are the priority.

#### Voices

| Name | Gender | Character |
|---|---|---|
| Dan | Male | Warm, clear, neutral American |
| Sam | Female | Calm, professional |
| Adam | Male | Deep, authoritative |
| Hope | Female | Bright, friendly |

---

### Gemini

Real audio generation using Google's TTS API. Always runs in **per_scene** mode: each scene is a separate API call, saved as `audio/scene_NN.mp3`. Durations are measured directly from the output MP3.

**Cost:** Google API quota per scene.
**Best when:** You want to try a different voice palette, or when ElevenLabs credits are limited.

#### Voices

| Name | Character |
|---|---|
| Zephyr | Bright, upbeat — default |
| Puck | Upbeat, energetic |
| Aoede | Warm, expressive |
| Kore | Firm, clear |
| Fenrir | Grounded, measured |

---

### Fake

No API calls. Assigns 3.0s to every scene and writes no audio files. Sets `tts.provider = "fake"` in `script.json`.

**Cost:** Free.
**Best when:** Testing layout, timing, or the pipeline without spending API credits.

---

## Selection guidance

- Default recommendation: **ElevenLabs, Dan** — used in most existing videos for consistency.
- Use **Gemini** if ElevenLabs is unavailable or the user wants to compare voices.
- Use **Fake** for any pipeline test where audio quality doesn't matter.
- If the user is unsure: suggest ElevenLabs + Dan and let them confirm.
