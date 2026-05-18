---
name: video-html
description: Generates HTML slides for each scene in a video project. Use when pipeline.script is complete and HTML slides are needed. Includes a script evaluation pre-pass that can propose scene splits or speech adjustments with human approval. Supports Mode C (AI-generated image per scene) or Mode D (full toolkit with HTML templates, SVG, and per-scene image generation). Presents a scene plan for user approval before generating anything.
compatibility: Requires Python 3, GOOGLE_API_KEY in generation/tools/.env, and internet access for Gemini image generation.
---

# video-html

Generate HTML slides for a video.

## Path detection

Extract UNIT, LESSON, and VIDEO from the user's message, or from session context if continuing from a previous step. Only ask if genuinely unknown.

Use `execute` to list `generation/units/$UNIT/lessons/` and match LESSON to the closest folder name as LESSON_SLUG. If the unit directory doesn't exist, stop with `❌ Unit "$UNIT" not found.` If nothing matches, stop with `❌ No lesson matching "$LESSON" found.` If you fuzzy-matched, show `⚠️  Resolved "$LESSON" → "$LESSON_SLUG"`.

- Video root: `generation/units/$UNIT/lessons/$LESSON_SLUG/videos/$VIDEO/`
- Script path: `<video-root>/script.json`
- Scenes dir: `<video-root>/scenes/`
- Images dir: `<video-root>/images/`
- Image src paths in HTML must use the full path from project root with a leading `/`:
  `/generation/units/$UNIT/lessons/$LESSON_SLUG/videos/$VIDEO/images/<filename>`

All steps below use VIDEO_ROOT derived above.

## Prerequisites

- `pipeline.script` must be `"complete"` in `script.json`
- Check `pipeline.audio`: if `"complete"`, present the audio check-in at Step 2 before proceeding
- Scripts are bundled in `backend/skills/video-html/scripts/`

## Gotchas

- **Images must use a leading `/` in the src path.** `embed-data.py` recognizes local files only when `src` starts with `/`, `file://`, or a drive letter (`C:\`). A bare relative path is silently skipped — the image is never embedded and will fail to load in the player.
- **AUDIO_LOCKED skips Step 3a entirely.** If the user declines to regenerate audio in Step 2, scene splits and speech edits are disabled for the whole session — no evaluation runs regardless of content.
- **gemini-image-gen.py may print a Windows absolute path.** Extract only the filename from stdout — e.g. from `C:\Users\...\generated_image_abc.png`, use only `generated_image_abc.png` when constructing the `src` attribute.

## Workflow Progress

Copy this checklist into your reply at the start of a session:

- [ ] Step 1: Script read (base64_clean + full script_cleaned.json)
- [ ] Step 2: Audio check-in (if pipeline.audio == "complete")
- [ ] Step 3: Mode confirmed (C / D)
- [ ] Step 3a (Mode D only): Script evaluation (splits / speech edits proposed if needed; approval if changes)
- [ ] Step 4: Planning context loaded
- [ ] Step 5: Scene plan approved by user (Round 1 — template + approach)
- [ ] Step 6: Content spec approved by user (Round 2 — exact copy + SVG structure) [Mode D only]
- [ ] Step 7: Generation context loaded
- [ ] Step 8: HTML generated (all scenes)
- [ ] Step 9: Scene files saved to scenes/
- [ ] Step 10: pipeline.html = "complete" set

---

## Step 1: Read Script Safely

Use `execute` to run base64_clean:
```bash
python backend/skills/video-html/scripts/base64_clean.py $VIDEO_ROOT/script.json
```
Read the **entire** `$VIDEO_ROOT/script_cleaned.json` before assessing any individual scene. Never read the raw `script.json` — it may contain base64 image data.

---

## Step 2: Audio Check-In

**If `pipeline.audio == "complete"`, run the audio check-in:**

> ⚠️  Audio has already been generated for this video.
> Do you plan to regenerate audio after updating the HTML?
> - **Yes** — I'll regenerate. Script edits (splits, speech adjustments) are enabled.
> - **No** — Keep existing audio. Script edits are disabled.

If **Yes**: Use `execute` to run:
```bash
python backend/skills/video-html/scripts/update-pipeline.py $VIDEO_ROOT/script.json audio=pending audio_tags=pending
```
Set AUDIO_LOCKED = false.

If **No**: Set AUDIO_LOCKED = true. Print:
> Audio locked — scene splits and speech edits are disabled.

**If `pipeline.audio` is not `"complete"`**, set AUDIO_LOCKED = false and proceed directly to Step 3.

Script evaluation runs in Step 3a (Mode D only) — not here.

---

## Step 3: Mode Check-In

Use `load_skill_resource` to read `references/mode-selection.md` and present the mode options to the user exactly as described there. Wait for their response before continuing.

---

## Step 3a: Script Evaluation (Mode D only)

**Skip this step entirely for Mode C.**

If AUDIO_LOCKED = true: print "Audio locked — scene splits and speech edits are disabled." and proceed to Step 4.

Otherwise: use `load_skill_resource` to read `references/script-editing.md` and follow its evaluation process.
- If no edits are needed: print the "No script edits needed" message and continue to Step 4.
- If edits are proposed: present them for approval (format in script-editing.md), wait for response, iterate if the user requests modifications, then apply approved edits to script.json before continuing to Step 4.

---

## Step 4: Load Planning Context

Load only what's needed to plan slides:

**Always load:**
- Use `load_skill_resource` to read `references/template-selection.md` — visual approach overview and template catalog for planning

**For Mode C, or Mode D plans that include any Image Gen scenes:**
- Use `load_skill_resource` to read `references/image-generation.md` — Visual Director formula and prompt assembly process

**Only if creating a new template from scratch (not for routine generation):**
- Use `load_skill_resource` to read `references/design-guide.md` — color palette, typography scale, layout constraints for template authoring
- Use `load_skill_resource` to read `assets/boilerplate.html` — canonical boilerplate CSS block to copy into the new template

Do not load individual HTML templates yet — load only the ones needed for the approved scene plan in Step 5.

---

## Step 5: Scene Plan (present for approval — do not generate until approved)

### 5a: Visual Preset (Mode C always; Mode D when any scenes use Image Gen)

If any scenes will use Image Gen, declare the Visual Preset as part of the plan:

```
Visual Preset:  [Minimal_Vector | Textured_Editorial | Digital_Glass]
Rationale:      [one sentence on why this preset fits the video's tone and subject matter]
```

Include this above the scene plan table — it will be approved together with the rest of the plan in Step 5c.

### 5b: Scene Plan Table

Produce a table for every scene:

| Scene | Template | Approach | Notes |
|-------|----------|----------|-------|
| 1 | e.g. `title-slide` | Text | Eyebrow: "Unit 1", Title: "..." |
| 2 | e.g. `svg-bar-chart` | SVG | Prompt card: "The dog barked at the..."; 5 words |
| 3 | e.g. `header-with-image` | Image Gen | Technical_Spec: Graphic_Staging; office setting, person at desk |

**Approach** must be one of: `Text`, `SVG`, or `Image Gen`.

For any `Image Gen` scene, Notes must include the planned Technical_Spec and a brief Environment + Subject description.

### 5c: Connected Sequences

After the table, identify any connected sequences — groups of scenes sharing the same example, metaphor, or concept thread. Define the visual vocabulary for each before any generation begins:

```
Sequence: Scenes [X–Y] — [brief description]
  - [Concept A] → [color/shape]
  - [Concept B] → [color/shape]
  - Arrow style: [e.g. 2px solid #292F36]
  - Font size for labels: [e.g. 1.25rem]
  - no-title: [yes/no]
```

**Wait for user approval of the full scene plan (including Visual Preset if applicable) before generating any HTML.**

---

## Step 6: Content Spec (Mode D only — second approval before generation)

**Skip this step for Mode C.** Proceed directly to Step 7.

Produce a per-scene content spec for every scene in the approved plan. Present all scenes at once as a single block. Wait for explicit user approval before proceeding to Step 7.

If the user requests edits, update the affected spec blocks and re-present only those scenes before continuing.

### Spec format by template type

**Text slides** (`title-slide`, `big-quote`, `code-slide`):

```
Scene N | title-slide
  Eyebrow: "..."         ← omit line if not used
  Title: "..."
  Subtitle: "..."        ← omit line if not used

Scene N | big-quote | quote-mark: [yes/no]
  Term: "..."
  Definition: "..."
```

**SVG slides** (`header-with-svg`, `bullets-with-svg`):

```
Scene N | header-with-svg | no-title: [yes/no] | viewBox: 1440×[660|820] | Pattern: [name or "custom"]
  Heading: "..."                              ← omit if no-title: yes
  Sequence: [name] (Scenes X–Y)               ← omit if not in a sequence
  [Left] Role: vague (#8B9199) | Badge: "..." | Content: "..." | Response: "..."
  [Right] Role: specific (#0093A4) | Badge: "..." | Content: "..." | Response: "..."
  Bottom: "..."                               ← omit if no bottom label
```

Pattern names come from `references/svg-patterns.md`. For custom SVGs, replace element lines with a structural description:

```
  Structure: [brief layout description, e.g. "chat window, user bubble right, AI bubble left, 2 exchanges"]
  [UserBubble 1]: "..."
  [AIBubble 1]: "..."
  [Annotation 1]: "..." (color: error/success/neutral)
  [UserBubble 2 (revised)]: "..."
  [AIBubble 2]: "..."
  [Annotation 2]: "..."
```

**Image gen slides** (Mode D with Image Gen):

```
Scene N | header-with-image
  Heading: "..."
  Image prompt: "[full assembled prompt]"
  Technical_Spec: [value]
```

### What this step locks in

- All copy: headings, labels, terms, definitions, captions, bottom text
- SVG pattern selection and viewBox
- no-title decision
- Color and role assignments per SVG element
- Sequence membership

After approval, **no copy decisions and no layout decisions remain** — Step 8 is rendering only.

---

## Step 7: Load Generation Context

Once the content spec is approved, load only the templates and tools the plan actually calls for:

**Always load:**
- Use `load_skill_resource` to read `references/generation-guide.md` — script alignment, connected sequences, slide text density, HTML requirements
- Use `load_skill_resource` to read `references/svg-patterns.md` — layout conventions and procedures for named SVG patterns (Mode D only)

**Load each template that appears in the approved plan** (not all — only the ones being used):
- For Mode C: use `load_skill_resource` to read `assets/full-image.html`
- For Mode D: use `load_skill_resource` to read each named template (e.g. `assets/title-slide.html`, `assets/svg-bar-chart.html`, etc.)
- This includes SVG pattern templates (`svg-flow`, `svg-bar-chart`, `svg-word-display`) — load only the specific ones in the plan, not all three.

**If any Image Gen scenes exist (always for Mode C; per plan for Mode D):**
- `backend/skills/video-html/scripts/gemini-image-gen.py`

---

## Step 8: Generate HTML

### Mode C — AI-Generated Images

For each scene:
1. Copy `full-image.html` as the starting point
2. Follow the **Image Gen Process** section below to generate the image and replace the placeholder

### Mode D — HTML Templates

Each scene uses whatever approach the approved plan specifies.

**For Text and SVG scenes:**
- Copy the approved template as the starting point — do not write slides from scratch
- Replace all `ALL_CAPS` placeholder text (e.g. `SLIDE_TITLE`, `BULLET_LEAD_1`) using the exact copy from the approved Step 6 content spec. Do not re-derive copy from the script — use the spec values verbatim.
- Delete optional elements (eyebrow labels, captions) if the scene does not need them
- **Do not modify the boilerplate `<style>` block** marked "do not modify"

**For Image Gen scenes:** follow the **Image Gen Process** section below.

#### SVG scenes

**If the template is `svg-flow`, `svg-bar-chart`, or `svg-word-display`:**
- Copy the template file directly as the starting point — it is the complete slide
- Replace all `ALL_CAPS` placeholders with scene content
- The viewBox is already correct for each pattern (see the template catalog in `references/template-selection.md`)

**If the template is `header-with-svg` or `bullets-with-svg`:**
- Copy the layout template as the starting point
- Write the inner `<svg>` from scratch; insert it into the `<div class="svg-area">`, replacing it
- viewBox defaults: `header-with-svg` with title `"0 0 1440 660"`, no-title `"0 0 1440 820"`; `bullets-with-svg` column `"0 0 540 640"`
- **If the approved spec names a pattern** (e.g. `Pattern: two-column-comparison`): apply the layout conventions from `references/svg-patterns.md` for that pattern. Use the y_cursor procedure and standard sizing defaults — do not recalculate geometry from scratch.
- **If the approved spec says `Pattern: custom`**: design coordinates from scratch using the structure description in the spec.

**Both paths:**
- Use brand color hex values in SVG attributes — CSS custom properties do not apply inside `<svg>`
- Apply the visual vocabulary defined in Step 5c — do not vary element sizes, colors, or styles within a sequence
- Embed the sequence vocabulary as an HTML comment at the top of each connected slide's `<body>`:
  ```html
  <!-- Sequence: [name] | [ConceptA]=teal | [ConceptB]=purple | arrows=2px #292F36 -->
  ```

### Image Gen Process

*(Used by Mode C for all scenes; by Mode D for designated Image Gen scenes.)*

1. Use the Visual Preset declared in Step 5a
2. Assemble the prompt using the formula in `references/image-generation.md`
3. Use `execute` to run:
   ```bash
   python backend/skills/video-html/scripts/gemini-image-gen.py "FINAL_PROMPT" --aspect-ratio 16:9 --output-dir $VIDEO_ROOT/images
   ```
   Add `--reference-image /path/to/prior_scene.png` for connected image sequences.
4. Capture the filename from the filepath printed to stdout. The tool may print an absolute Windows path — extract just the filename.
5. Replace the `<div class="image-placeholder">` in the template with:
   ```html
   <img src="/<VIDEO_ROOT>/images/generated_image_abc.png" alt="brief description" class="image">
   ```
   Use the VIDEO_ROOT path detected at the top of this skill (e.g. `/generation/units/my-unit/lessons/my-lesson/videos/my-video/images/...`).

   See Gotchas — always use a leading `/`.

---

## Step 9: Save Scene Files

```
$VIDEO_ROOT/scenes/scene_01.html
$VIDEO_ROOT/scenes/scene_02.html
...
```

Zero-pad to 2 digits. Each file is a complete self-contained HTML document (from `<!DOCTYPE html>` to `</html>`).

HTML files are **not** inserted into `script.json` at this stage — `embed-data.py` reads them directly from the `scenes/` folder during assembly.

---

## Step 10: Update script.json

Use `execute` to run the appropriate command based on the mode used:

**Mode C:**
```bash
python backend/skills/video-html/scripts/update-pipeline.py $VIDEO_ROOT/script.json html=complete html_mode=ai_images
```

**Mode D — no image gen used:**
```bash
python backend/skills/video-html/scripts/update-pipeline.py $VIDEO_ROOT/script.json html=complete html_mode=html_templates_only
```

**Mode D — image gen used for one or more scenes:**
```bash
python backend/skills/video-html/scripts/update-pipeline.py $VIDEO_ROOT/script.json html=complete html_mode=html_including_image_templates
```

Ask: "Ready to add TTS expression tags to the narration? Say yes to continue, or ask any questions about the slides first."
