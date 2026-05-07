# Image Generation

When to use AI-generated images and how to produce prompts using the Visual Director process. The component library referenced here lives in `assets/prompt-framework.json`.

---

## When to Use AI Images

Use when the scene:
- Is built around a metaphor or analogy that benefits from a real-world visual (e.g. "AI is like an improv performer")
- Introduces an abstract concept where an illustration aids comprehension
- Is intended to create a specific *feeling* or visual tone rather than explain something precisely
- Describes a real-world context (a classroom, a data center, a conversation)

**When NOT to use:** Avoid for data, charts, statistics, or any content where accuracy matters — generated images of numbers or charts are unreliable. Use SVG instead.

**Placement:** Use `header-with-image` when the image is the entire visual, `two-column-quote-with-image` when pairing with a key term or quote, or `bullets-with-image` when pairing with 2–3 takeaway points.

---

## Tool: `scripts/gemini-image-gen.py`

```bash
python scripts/gemini-image-gen.py "<prompt>" --aspect-ratio RATIO --output-dir PATH
```

- `--aspect-ratio` — one of `1:1`, `9:16`, `16:9`, `4:3`, `3:4` (default: `16:9`)
- `--output-dir` — optional output directory (default: `generation/tools/generated-images/`)

**Output:** The filepath of the saved image is printed to stdout — nothing else. On Windows, this may be an absolute path. Extract just the filename, then construct the src as a leading-slash project-root-relative path (e.g. `/generation/units/UNIT/lessons/LESSON/videos/VIDEO/images/filename.png`). Use the VIDEO_ROOT resolved at the start of the skill. See Gotchas in SKILL.md — `embed-data.py` requires the leading `/` to recognize it as a local file.

---

## Visual Director Process

### Before you begin

Confirm the video-level Visual Preset from the Video Visual Constants block (Step 5a in the skill). This is set **once per video** — do not re-select per scene.

**Visual_Preset:** one of `Minimal_Vector`, `Textured_Editorial`, `Digital_Glass` — defined in `assets/prompt-framework.json`.

### Step 1 — Build Subject + Context

**Layer 1 — Environment:** One sentence describing the setting.
- Keep it simple and physical: surfaces, lighting temperature, spatial scale.
- Example: *"A softly lit minimal workspace with warm wooden surfaces and a dark background."*

**Layer 2 — Subject + Action:** One sentence describing the primary subject and what it's doing.
- If the narration names a concrete real-world subject (a dog, a stage, a mailbox), depict it literally. If the scene is abstract or conceptual, use abstract geometric forms. Do not default to abstraction when a literal subject fits.
- Be specific. Not *"a robot"* but *"a small friendly white robot with rounded edges holding a glowing data cube at arm's length."*

### Step 2 — Select Technical_Spec

Choose from `assets/prompt-framework.json`'s `Technical_Specs` based on the target template:

| Template | Technical_Spec | Flag |
|---|---|---|
| `header-with-image` (conceptual/metaphor) | `Graphic_Staging` | `--aspect-ratio 16:9` |
| `header-with-image` (technical/spatial) | `Isometric_Structure` | `--aspect-ratio 16:9` |
| `two-column-quote-with-image` | `Vertical_Hierarchy` | `--aspect-ratio 9:16` |
| `bullets-with-image` | `Vertical_Hierarchy` | `--aspect-ratio 9:16` |

Use `Isometric_Structure` for scenes about systems, networks, servers, code execution, or spatial/technical architecture. Use `Graphic_Staging` for metaphors, analogies, and human contexts.

### Step 3 — Check for sequence reference

If this scene is part of a connected image sequence and a prior scene's image already exists on disk, pass it with `--reference-image /path/to/prior_scene.png`. This is the primary visual continuity mechanism — Gemini replicates character, setting, and style from the reference image. Optionally also add `Optional_Modifiers.Sequence_Anchor` to the prompt as supplementary text guidance.

If this is the first image in the sequence, skip this step.

### Step 4 — Check for subject energy

- Narration about motion, breakthrough, discovery, or energy → add `Optional_Modifiers.Dynamic_Action`
- Narration about clarity, stillness, or reflection → add `Optional_Modifiers.Calm_Focus`
- Neither clearly applies → add nothing

### Step 5 — Assemble

Use this formula in this exact order:

```
Create an image of [Layer 1 — Environment]. [Layer 2 — Subject + Action]. [Visual_Preset]. [Technical_Spec]. [Defaults.Clean_Design]. [Defaults.Simple_Environment]. [Defaults.Slide_Safe_Zone]. [Defaults.Complementary_Palette]. [Optional_Modifiers if applicable].
```

All four `Defaults` are always included — never omit them.

---

## Output Format

For each image scene, produce:

**Final Prompt:** *(the fully assembled string — ready to pass to gemini-image-gen.py)*  
**aspect-ratio flag:** *(e.g. `--aspect-ratio 9:16`)*  
**--reference-image flag:** *(path to prior scene's image if part of a connected sequence; omit otherwise)*  
**Visual Rationale:** *(one sentence: why this subject and composition fit the scene)*

---

## Example

**Scene narration:** *"The model looks at 'The dog barked' and assigns a probability to every possible next word."*  
**Template:** `bullets-with-image` → `Vertical_Hierarchy`  
**Visual_Preset:** `Minimal_Vector`

**Layer 1:** A clean abstract space with soft geometric background planes in muted cool tones.  
**Layer 2:** A central glowing node radiates outward with multiple colorful probability beams of varying thickness extending in different directions, each beam a distinct saturated hue.

**Final Prompt:**
> Create an image of a clean abstract space with soft geometric background planes in muted cool tones. A central glowing node radiates outward with multiple colorful probability beams of varying thickness extending in different directions, each beam a distinct saturated hue. Clean vector illustration, strong precise linework, hard-edged geometric shading, clean bezier curves, consistent line-weight, harmonious limited color palette, matte finish. Vertical portrait composition, 9:16 aspect ratio, bottom-to-top visual flow, flat orthographic rendering. A clean, wordless design entirely devoid of letters, numbers, or symbols. A minimalist environment with large areas of empty space. All essential action and subjects are strictly contained within the inner 60% of the frame. The outer margins remain empty. Muted, desaturated tones in all background and environmental elements. Saturated color is reserved for the primary subject only. The overall palette harmonizes with a teal and purple branded interface without competing.

**aspect-ratio flag:** `--aspect-ratio 9:16`  
**Visual Rationale:** Abstract radiating beams convey next-word prediction without text, fitting the data-visualization nature of the scene.
