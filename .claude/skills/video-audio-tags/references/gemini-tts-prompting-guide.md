# Gemini TTS Prompting Guide

Reference for generating `gemini` audio tags in `/video-audio-tags`. Covers the full tag list and advanced prompting strategies.

---

## Audio Tags

Tags are inline modifiers like `[whispers]` or `[excitedly]` that give granular control over delivery. Place them at the start of a scene for overall tone, or inline before specific phrases.

### Commonly used tags

| | | | |
|---|---|---|---|
| `[amazed]` | `[crying]` | `[curious]` | `[excited]` |
| `[sighs]` | `[gasp]` | `[giggles]` | `[laughs]` |
| `[mischievously]` | `[panicked]` | `[sarcastic]` | `[serious]` |
| `[shouting]` | `[tired]` | `[trembling]` | `[whispers]` |

### Educational content tags (recommended)

| Tag | Use when |
|---|---|
| `[warmly]` | Welcoming, inviting delivery — introductions, encouragement |
| `[clearly]` | Articulate, precise — defining terms, key facts |
| `[deliberately]` | Measured, intentional — complex concepts, step-by-step explanations |
| `[curious]` | Inquisitive tone — posing questions, setting up an exploration |
| `[excitedly]` | High energy — surprising results, big reveals |
| `[thoughtfully]` | Reflective — deeper implications, connecting ideas |
| `[seriously]` | Focused, important — warnings, critical distinctions |
| `[amazed]` | Genuine delight — surprising facts, elegant solutions |

### Pace tags

- `[very fast]` — rapid delivery
- `[very slow]` — deliberate, drawn-out
- `[energetically]` — upbeat, brisk

### Combination tags

Tags can be combined creatively:
- `[excitedly, very fast]` — rapid enthusiasm
- `[sarcastically, one painfully slow word at a time]` — exaggerated sarcasm

---

## Advanced Prompting

The `gemini-audio-gen.py` script automatically wraps each scene's `gemini` text in a persona prompt. The tags you write in the `gemini` field are placed in the `### TRANSCRIPT` section of that prompt.

The hardcoded persona used by the script:

```
# AUDIO PROFILE: Educational Narrator
## "The Clear Explainer"

### DIRECTOR'S NOTES
Style: Clear, warm, and engaging educator. Patient and encouraging without being condescending.
Pace: Moderate, with natural variation — slower for key concepts, slightly faster for transitions.

### TRANSCRIPT
{your gemini text here}
```

### What this means for tagging

- The persona already sets a warm, clear, moderate baseline — you don't need to establish tone from scratch in every scene
- Use tags to **deviate** from the baseline: add excitement for reveals, deliberateness for definitions, curiosity for questions
- Tags that reinforce the baseline (e.g., `[clearly]` on every scene) add little value — reserve them for contrast

---

## Tips

- Keep the actual speech text unchanged — only add tags, do not reword
- English tags work best even if the transcript is in another language
- No exhaustive list of supported tags exists — experiment freely; the model interprets natural language modifiers
- If a tag isn't producing the desired effect, try a more descriptive phrase: `[with genuine amazement]` vs `[amazed]`
