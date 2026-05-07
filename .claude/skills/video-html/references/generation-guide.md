# Slide Generation Guide

Generation-phase guidance: how to align slides to their scenes, handle connected sequences, and meet technical requirements. Load this file at Step 6, once the scene plan is approved.

For visual approach selection and the template catalog, see `template-selection.md`.
For colors, typography, and layout design principles, see `design-guide.md`.

---

## Image Generation Workflow

See `image-generation.md` for the full Visual Director process, prompt assembly formula, and tool reference. Do not write freeform prompts — use the formula.

> **Tip — editing a production script:** If a `script.json` already has base64 images embedded, run `scripts/base64_clean.py` first to strip the payloads. Re-run `/video-assemble` afterward to restore them.

---

## Script Alignment Process

**Before generating any slides, read the entire script.** Do not assess scenes one at a time in isolation — connected sequences need to be identified first and planned as a group (see below).

When assessing each scene, ask:

1. **What is this scene communicating?** A fact, a definition, a process, an analogy, or an example?
2. **Does the content have inherent visual structure?** Lists and steps → text slide. Flow or data → SVG. Metaphor or mood → image.
3. **How long is the scene?** Short scenes (under 5s) suit simple slides (big-quote, title-slide). Longer scenes support richer layouts.
4. **Is precision required?** If numbers or structured relationships matter, prefer SVG over image generation.
5. **Does a template serve this scene, or would a custom approach be better?** Templates are a starting point — if a purpose-built SVG or a different layout would serve the scene more directly, use that instead.
6. **Is this scene part of a connected sequence?** See below.

---

## Identifying and Handling Connected Sequences

A connected sequence is a group of consecutive scenes that share the same example, metaphor, or concept thread. Scenes in a sequence must use a consistent visual language — the same color-to-concept mapping, element sizing, and diagram style — so the viewer perceives them as one continuous explanation rather than unrelated slides.

### Signals that scenes form a sequence

Look for these patterns when reading the script:

- **Continuation language:** "the same way," "this is why," "let's see," "as we just saw," "now watch what happens when..." — these phrases explicitly link a scene to the one before it
- **A shared example carried across scenes:** an example introduced in one scene and extended or resolved in the next 1–3 scenes
- **Setup → payoff structure:** one scene poses a question or introduces a term; the next scene answers or illustrates it
- **The same subject matter in the same template type across consecutive scenes:** e.g. three consecutive `header-with-svg` entries that all deal with the same concept
- **Definition followed immediately by application:** a `big-quote` defining a term, then a `header-with-svg` or `bullets-with-svg` showing how that term works

### What to do when you find a sequence

1. **Identify the full extent of the sequence** before generating any of its slides — know where it starts and ends
2. **Define a visual vocabulary for the sequence:** decide which color represents which concept and which shapes/elements will be reused. Write this down as a comment or note before generating. Example:
   - User input → teal box
   - AI processing → purple box
   - Output → gray box
   - Arrows → 2px solid `#292F36`
3. **Generate the slides in order**, using the first slide's visual treatment as the explicit reference for each subsequent one. If generating via an LLM, include the first slide's SVG or layout as context when generating the next.
4. **Keep element sizes and proportions consistent** across the sequence — same font sizes for equivalent text, same box dimensions, same arrow styles, same padding
5. **Use the `no-title` toggle consistently** within a sequence — if one scene hides the title to let the diagram breathe, the connected scenes should match

---

## Slide Text Density

**Slides accompany narration — they do not replace it.** The narration carries the explanation; the slide reinforces the key point visually. Keep slides minimal:

- **`title-slide`**: title + optional subtitle only. No body text.
- **`code-slide`**: the code speaks for itself; annotation is optional and one line max.
- **`big-quote`**: term (1–4 words) + one-line definition. No additional text.
- **`header-with-image`** / **`header-with-svg`**: heading only — max 8 words. No body text whatsoever.
- **`two-column-quote-with-image`**: heading (2–8 words) + one subheading sentence. No bullets or paragraphs.
- **`bullets-with-image`** / **`bullets-with-svg`**: heading + max 3 bullets × 4–5 words each. The 3.25rem font enforces this — longer text wraps badly.

If you feel compelled to write a paragraph, a sentence of explanation, or more than 3 bullets, that content belongs in the narration. Move it there and shorten the slide.

---

## HTML Generation Requirements

### Every slide must be self-contained
- No external dependencies except Google Fonts
- Images referenced by leading-slash local file path during drafting (e.g. `/generation/units/.../images/file.png`); `embed-data.py` converts them to base64 data URIs for final production
- SVGs embedded inline — no external SVG files

### Use the Templates
The templates provide the designated structure for the slides, with dedicated areas for text to be inserted. Avoid deviating from the template.

### Why all sizes use rem

Slides are designed at 1600×900px. The `:root` sets `font-size: calc(16vh / 9)`, which makes `1rem = 16px` at the design height of 900px. As the player iframe resizes, `1vh` changes proportionally, so all rem values scale together — identical behavior to the old `transform: scale()` approach, just implemented in CSS. Use `rem` for all font sizes, padding, margins, widths, and heights. Do not use bare `px` for layout values.

### Color usage rules
- All colors via CSS variables — no hardcoded hex values in template-specific styles
- Reserve `var(--color-aqua)` exclusively for slides about AI features
- Use semantic colors appropriately: `var(--color-error)` for mistakes/warnings, `var(--color-success)` for correct answers, etc.

---

## Animation Guidelines

- CSS keyframe animations and transitions are encouraged
- **Entrance animations** (fire once on load): fade-in, slide-up, scale-in — keep duration around 400ms
- **Ambient/looping animations**: floating, pulsing, shimmer — fine for background elements
- **Do not use time-based animations** intended to sync with specific narration moments — the player has no mechanism to trigger these. Animations should be self-contained and meaningful at any point during the scene.
