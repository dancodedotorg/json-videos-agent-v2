# Mode Selection

## Modes

### Mode C — AI-Generated Images

Every scene gets a full-canvas AI-generated image. The same `full-image.html` template is used throughout — the generated image fills the slide. No per-scene template decisions are needed.

**When Mode C fits:**
- The video's content is primarily metaphorical, atmospheric, or narrative
- A consistent illustrated look across all scenes is more important than visual variety
- The user wants to move quickly without per-scene discernment
- All scenes benefit from image-based visuals (no data charts, code, or structured diagrams)

**html_mode value:** `ai_images`

---

### Mode D — HTML Templates

Each scene is assessed individually and gets the visual treatment that best fits its content: HTML/CSS templates, inline SVG, or AI-generated images — whichever serves the scene. AI image generation is part of the Mode D toolkit; use it for scenes where an image adds value (metaphors, atmosphere, real-world context). It is not excluded.

**When Mode D fits:**
- Scene content varies across the video (definitions, processes, diagrams, examples, analogies, data)
- Some scenes need structured visuals — SVG, bullet lists, code, or data charts — that image gen cannot produce reliably
- The visual approach should match each scene's content rather than apply a uniform treatment

**html_mode value depends on what was generated:**
- `html_templates_only` — Mode D, no image gen used in any scene
- `html_including_image_templates` — Mode D, image gen used for one or more scenes

---

## Check-In Presentation

Present the following to the user at Step 3:

> **HTML generation mode for "$ARGUMENTS":**
>
> - **C — AI-Generated Images** *(fast, uniform)*
>   Generates one AI image per scene using Gemini and inserts it as a full-width `<img>`. Every scene gets an AI image — no per-scene discernment required. Best when you want a consistent illustrated look across all scenes.
>
> - **D — HTML Templates** *(most flexible, requires discernment)*
>   Builds slides using the full toolkit: HTML/CSS templates, inline SVG diagrams, and AI-generated images — whichever is most appropriate per scene. Each scene is assessed individually. Image gen is available and used when a realistic visual or atmosphere adds value. Best when scene content varies (definitions, diagrams, examples, summaries).
>
> Which mode? (C / D)
