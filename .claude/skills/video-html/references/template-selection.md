# Template Selection

Visual approach overview and template catalog for planning slides. Load this file at Step 4, before building the scene plan.

For connected sequences, slide density rules, and HTML requirements, see `generation-guide.md`.
For colors, typography, and layout design principles, see `design-guide.md`.

---

## Choosing a Visual Approach

Every scene in a video script needs a visual. There are three ways to produce one, and they serve different purposes.

### 1. Text-Based Slides (HTML templates)

**Use when the scene is:**
- Defining a vocabulary term or concept
- Presenting a list of key points, steps, or rules
- Showing a chapter title, section intro, or closing summary
- Displaying a code example
- Delivering a single high-impact idea (a quote, stat, or key phrase)
- Explaining something where the structure of the information *is* the visual

**Why:** HTML/CSS slides are fast, scalable, and perfectly on-brand. They require no external tools and can be generated entirely by an LLM using the templates in this folder.

**Templates available:** `title-slide`, `code-slide`, `big-quote`, `header-with-image`, `header-with-svg`, `two-column-quote-with-image`, `bullets-with-image`, `bullets-with-svg`

---

### 2. AI Image Generation

**Use when the scene is:**
- Built around a metaphor or analogy that benefits from a real-world visual (e.g. "AI is like an improv performer")
- Introducing an abstract concept where an illustration aids comprehension
- Intended to create a specific *feeling* or set a visual tone rather than explain something precisely
- Describing a real-world context (a classroom, a data center, a conversation)

**Why:** Generated images excel at atmosphere and illustration. They give metaphors and analogies visual weight that pure text or diagrams cannot. Use `header-with-image` when the image is the entire visual, `two-column-quote-with-image` when pairing with a key term or quote, or `bullets-with-image` when pairing with 2–3 takeaway points.

**When NOT to use:** Avoid image generation for data, charts, statistics, or any content where accuracy matters — generated images of numbers or charts are unreliable.

**Tool:** `scripts/gemini-image-gen.py` — see `image-generation.md` for the full Visual Director prompt assembly process.

---

### 3. SVG Generation

**Use when the scene is:**
- Visualizing a flow, process, or sequence (boxes and arrows)
- Displaying data with real numbers (probability charts, bar charts, comparisons)
- Showing a structured diagram where relationships between elements matter
- Presenting a fill-in-the-blank or sentence-completion concept where text layout is the point
- Any case where precision matters and an image would be fuzzy or inaccurate

**Why:** LLMs can generate SVG reliably for structured content. SVGs embed directly in slide HTML with no extra production steps — no API calls, no base64 conversion. They scale perfectly and can use the brand color system via inline styles.

**Good SVG candidates:** Flow diagrams, probability visualizations, word-weight charts, annotated sentence displays, comparison grids, simple icon-style illustrations.

**Avoid SVG for:** Complex realistic illustrations, photos, or scenes requiring artistic rendering.

**SVG templates:** `svg-flow`, `svg-bar-chart`, and `svg-word-display` are standalone full-canvas templates — use them directly as the complete slide for their respective diagram types. See the Template Catalog below for details. For custom diagrams that don't fit any of these patterns, use `header-with-svg` or `bullets-with-svg`.

**After generating a new diagram type:** If you create an SVG diagram that has no existing pattern template, save a reusable version as a new `svg-*.html` file in `.claude/skills/video-html/assets/` once the script is complete. Follow the same ALL_CAPS placeholder convention as the existing patterns so future generations can use it without redesigning from scratch.

**For complex diagrams — consider ai-figure:** If a scene requires a diagram with many nodes in non-linear topology (decision trees, binary trees, neural network layers, ER diagrams, state machines, or arbitrary node graphs), manual coordinate placement becomes unreliable. In these cases, raise ai-figure ([https://github.com/hustcc/ai-figure](https://github.com/hustcc/ai-figure)) with the user before proceeding. ai-figure is a JS rendering engine that auto-lays out structured diagrams from a compact config — an LLM can call it as a Node tool alongside the existing Python tools. Discuss whether the complexity warrants adding it for that generation session.

---

### Choosing a Template

Before looking at any template, ask what the scene is *doing*: Is it defining something? Showing a relationship? Setting atmosphere? Illustrating data? Telling a story through a visual? Once you know that, browse the Template Catalog below to find what fits — or decide you need a custom SVG. The catalog is a menu, not a flowchart. A template that "almost fits" is not always better than a purpose-built SVG or an image that serves the scene directly.

Templates and image generation are not separate choices — `header-with-image`, `two-column-quote-with-image`, and `bullets-with-image` are layouts *for* a generated image; choosing the template and generating the image are the same decision. Likewise, `header-with-svg` and `bullets-with-svg` are open containers: write any SVG you need, not just the existing diagram patterns.

---

## Template Catalog

### `title-slide.html`
A high-impact, text-only slide where the title dominates the canvas. Typography is the visual — there's no image or diagram competing for attention.
**Example uses:** Opening or closing a video; introducing a new section; transitioning between major topics.
**Tip:** The eyebrow label is useful for section numbering (e.g. "Unit 3 · Lesson 2"). Delete it if not needed.

### `code-slide.html`
A dark-themed slide where the code block is the visual focus. The code speaks for itself; any surrounding text is minimal framing.
**Example uses:** Displaying and explaining a code example in any programming language.
**Tip:** Use inline `<span style="color: var(--code-keyword)">` etc. for syntax highlighting — no external library needed.

### `big-quote.html`
A declaration slide — one large term or phrase commands attention, with a single supporting line below. Text is everything; there's no image or diagram.
**Example uses:** Introducing a vocabulary term with its definition; landing a single key concept.
**Tip:** Delete the decorative quote mark when the content is a term or concept rather than a quoted phrase.
**Avoid when:** The scene has more than one concept to land, or when a visual alongside the term would aid comprehension — consider `two-column-quote-with-image` instead.

> **Three templates take a portrait image** — `header-with-image`, `two-column-quote-with-image`, and `bullets-with-image`. Choose based on how much text the scene needs alongside the image: none (`header-with-image`, image IS the content), a concept + one line (`two-column-quote-with-image`), or 2–3 short takeaways (`bullets-with-image`).

### `header-with-image.html`
The image does the heavy lifting — it fills most of the slide, with a single heading that frames the visual. No body text; the narration carries the explanation.
**Example uses:** Metaphors and analogies that benefit from a real-world or atmospheric visual; scenes meant to set a mood; moments where an illustration communicates more than text could.
**Tip:** Keep the heading to 8 words or fewer. Image generates at `--aspect-ratio 16:9`.

### `header-with-svg.html`
A flexible container for any custom SVG diagram, with an optional heading banner at top. The diagram is the visual; the heading frames it. Build the SVG from scratch — this template is not restricted to any existing pattern.
**Example uses:** Flow diagrams, annotated illustrations, process breakdowns, custom data displays, or any visual that doesn't fit an existing SVG pattern template.
**Tip:** Add `class="no-title"` to `<body>` to hide the heading and give the SVG the full canvas. Reference brand hex colors directly in SVG attributes (CSS variables don't apply inside `<svg>`).

### `two-column-quote-with-image.html`
Equal visual weight between a concept and an image — a large heading and subheading on the left, a portrait image on the right. Text and visual share the slide.
**Example uses:** Introducing a vocabulary term paired with an illustrative portrait image; a key concept alongside a character or context image.
**Tip:** Heading = the term or concept (2–8 words). Subheading = one framing sentence. No bullets or paragraphs. Image generates at `--aspect-ratio 9:16`.

### `bullets-with-image.html`
The text takes the lead — a short list of key points on the left, with a portrait image providing visual context on the right. The image supports; the bullets are the message.
**Example uses:** 2–3 key takeaways where a supporting visual adds context but isn't the main point; summarizing a concept with a grounding image alongside.
**Tip:** Max 3 bullets, 4–5 words each — the large font size wraps badly at longer lengths. Image generates at `--aspect-ratio 9:16`.

### `bullets-with-svg.html`
Like `bullets-with-image`, but with a custom SVG diagram in place of a photo — good when precision matters or the supporting visual is structural rather than atmospheric. Build the SVG from scratch for the right column.
**Example uses:** 2–3 takeaways paired with a diagram, data visualization, or annotated illustration that clarifies the bullets.
**Tip:** Max 3 bullets, 4–5 words each. The SVG column is narrower than a full-canvas SVG — design accordingly.

### `svg-flow.html`
A full-canvas flow diagram — boxes connected by arrows in a left-to-right sequence. Best for 3–4 clearly ordered stages where directionality is the point.
**Example uses:** Input → processing → output pipelines; step-by-step processes; showing how something moves through a system.
**Tip:** Box color convention: teal = input, purple = processing, gray = output. Follow this consistently within a sequence.

### `svg-bar-chart.html`
A full-canvas horizontal bar chart. Data is the visual — bars show ranked quantities or probabilities at a glance, with an optional prompt card framing the question.
**Example uses:** Showing ranked word probabilities; comparing frequency or likelihood across 3–5 options; any "more vs. less" relationship where relative size matters.
**Tip:** Top 2 bars render in teal to emphasize the leaders; remaining bars are gray. Scale: 600 SVG units = 100%.

### `svg-word-display.html`
A full-canvas sentence completion display — a fill-in-the-blank sentence at top, with probability pills arranged below showing likely next words by size and color.
**Example uses:** Word prediction activities; showing how AI completes a sentence; any "what comes next?" framing where the options and their relative likelihood are the visual.
**Tip:** Large purple pills = high probability; small gray pills = low probability. Use `<tspan>` elements inside a single `<text>` for mixed-color sentence text.
