# Slide Design System

**This is a template authoring reference** — use it when creating a new template from scratch. During normal slide generation, all design constraints (colors, spacing, typography, rem scaling) are already encoded in the templates and boilerplate. You do not need this file to generate slides from existing templates.

For guidance on choosing templates and generating HTML content, see `generation-guide.md`.

---

## Color Palette

**Primary Brand Colors:**
- Brand Teal: #0093A4 (active state, highlights, accent bars)
- Brand Purple: #8C52BA (primary accents, headings, decorative elements)
- Brand Aqua: #3CFFF7 — **AI features only. Do not use for general slide elements.**

**Semantic Colors:**
- Error Red: #E02D16
- Warning Yellow: #F9CB28
- Success Green: #3EA33E
- Info Blue: #1892E3

**Neutral Colors:**
- Text Primary: #292F36 (headings, primary text)
- Text Secondary: #4C5661 (body text)
- Light Gray: #F7F8FA (slide backgrounds)
- Medium Gray: #D1D4D8 (borders, dividers, placeholder fills)
- Dark Gray: #5F6872 (captions, labels, muted text)

All colors must be referenced via CSS custom properties — no hardcoded hex values in slide-specific styles:

```css
:root {
  --color-teal:           #0093A4;
  --color-purple:         #8C52BA;
  --color-aqua:           #3CFFF7; /* AI features only */
  --color-error:          #E02D16;
  --color-warning:        #F9CB28;
  --color-success:        #3EA33E;
  --color-info:           #1892E3;
  --color-text-primary:   #292F36;
  --color-text-secondary: #4C5661;
  --color-gray-light:     #F7F8FA;
  --color-gray-medium:    #D1D4D8;
  --color-gray-dark:      #5F6872;
}
```

---

## Typography

**Fonts:** Barlow Semi Condensed (headings, bullets, display text), Figtree (body, subheadings, captions)
**Icons:** SVG icons or Unicode symbols only — no external icon libraries.

Font import is included in the boilerplate — every slide already has it. If writing a new template from scratch, copy the full boilerplate block from `.claude/skills/video-html/assets/boilerplate.html` into `<head>`. Do not write the `:root` rule manually.

**Rem scaling:** All type sizes use `rem`. The boilerplate sets `:root { font-size: calc(16vh / 9) }`, making `1rem = 16px` at the design height of 900px. All rem values scale proportionally as the player resizes — never use bare `px` for font sizes, padding, margins, or layout dimensions.

**Type Scale:**

| rem | Role | When to use |
|---|---|---|
| 7rem | Dominant display — term | Text IS the entire slide; one word or short phrase that must own the canvas |
| 6.5rem | Dominant display — title | Full-slide title or chapter opener; one line of large centered text |
| 6rem | Large heading with companion | Primary heading when sharing the slide with a subheading or image |
| 4rem | Standard header banner | Framing label at the top of a content slide; used across most layouts |
| 3.25rem | Scannable bullets | Enumerable points read at a glance — enforce 4–5 words per bullet at this size |
| 2.25rem | Subheading / supporting sentence | One sentence elaborating or defining the heading above it |
| 2rem | Definition / body text | Short explanatory sentence below a dominant display element |
| 1.5rem | Eyebrow / section label | Small uppercase label for unit or section context above a title |
| 1rem | Caption / small annotation | Image captions, placeholder labels, secondary UI hints |

Headings, bullets, and display text → Barlow Semi Condensed weight 600.
Subheadings, body, and captions → Figtree weight 400 (600 for emphasis).

---

## Layout Principles

- **Spacing:** 8px grid system for all padding and margins
- **Cards:** White backgrounds, subtle box shadows, rounded corners (12px radius)
- **Grid:** 2-column and 3-column layouts as needed; columns separated by 48–64px gaps
- **Hierarchy:** Clear visual hierarchy using typography scale and color — one dominant element per slide
- **Aspect ratio:** All slides are 16:9 at 1600×900px

---

## Content Blocks

- **Cards:** White background (`#ffffff`), subtle shadow (`0 4px 16px rgba(0,0,0,0.08)`), 12px border radius
- **Accent bars:** 16px wide, full-height, brand teal — used to anchor left-aligned layouts
- **Dividers:** 1–4px height, medium gray or semi-transparent white depending on background
- **Layout options:** Full-width, 2-column (55/45 or 50/50 split), 3-column equal
