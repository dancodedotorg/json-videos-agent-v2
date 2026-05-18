# SVG Layout Conventions

Structural conventions and layout procedures for common SVG patterns used in `header-with-svg` slides. Reference the pattern name in the Step 6 content spec, then apply the relevant conventions when generating.

These are not lookup tables — they are defaults and procedures. Adjust element heights when content requires more lines; the surrounding coordinates follow from the rhythm rules below.

## When to use a named pattern vs. custom

Use a named pattern when the Step 6 spec names one and the scene's structure matches. Custom SVG is appropriate for unique layouts (chat windows with UI mockups, annotated diagrams without a standard structure) — design those from scratch.

---

## Text Fit Reference

SVG does not wrap text. Before writing any `<text>` element, estimate how many `<tspan>` lines the string needs.

**Formula:** `chars_per_line ≈ box_width / (0.58 × font-size)`

| font-size | 480px box | 560px box | 620px box | 700px box |
|-----------|-----------|-----------|-----------|-----------|
| 22        | ~37       | ~44       | ~49       | ~55       |
| 24        | ~34       | ~40       | ~44       | ~50       |
| 26        | ~32       | ~37       | ~41       | ~46       |
| 28        | ~29       | ~35       | ~38       | ~43       |
| 30        | ~27       | ~32       | ~35       | ~40       |

If a string exceeds the per-line estimate, split at a natural phrase break into 2 `<tspan>` lines. Add 34px between tspan baselines for font-size 22–26; add 38px for font-size 28–32.

---

## Layout Conventions (shared across patterns)

### Canvas and margins
- Standard canvas with header: `viewBox="0 0 1440 660"` — SVG area is approximately 560px tall after the 140px header
- Full canvas (no-title): `viewBox="0 0 1440 820"` — SVG area is approximately 720px tall
- Standard side margins: **60px** left and right
- Reserve **110px at the bottom** of the SVG area for a bottom label if the spec includes one

### Standard element sizing

These defaults work for most content. Adjust heights when text requires more lines (add 34px per extra line).

| Element | Default height | rx | Notes |
|---------|---------------|-----|-------|
| Badge (pill) | 50px | 25 | Pill shape; centered in column; label size=26, weight=600 |
| Content box (1 line) | 72px | 12 | ~50px for text + 11px top/bottom padding |
| Content box (2 lines) | 106px | 12 | 72 + 34 for second line |
| Content box (3 lines) | 140px | 12 | 72 + 34×2 |
| Arrow (vertical) | 54px total | — | 42px line + 12px arrowhead |
| Arrow (horizontal) | 80px gap | — | Line from box edge + arrowhead; arrowhead is 24×12px |
| Annotation badge | 48px | 10 | Short label; text centered; size=22, weight=600 |

### Vertical rhythm (top-down layout)

Use a `y_cursor` approach: start at the top of the SVG area (y≈20 with title, y≈30 no-title), advance by each element's height, then add the gap before the next element.

Standard gaps between element types:
- After badge → before content box: **18px**
- After content box → before vertical arrow: **10px**
- After arrow → before next box: **8px**
- After response/last box → before column label: **22px**
- After column label → before bottom label: **40px** (or pin bottom label at canvas_bottom − 110)

### Text positioning within a box

For a box at `rect_y` with height `h`:
- Single line: baseline ≈ `rect_y + (h × 0.65)` (accounts for cap height)
- Two lines: first baseline ≈ `rect_y + (h × 0.42)`, second = first + 34
- Header label at top of box (e.g. "AI Response:"): baseline = `rect_y + 34`, size=22, weight=600; content lines start +34px below that

### Horizontal alignment
- Left-aligned text inside a box: `x = box_x + 20`
- Center-aligned text in a column: `x = column_center_x`, `text-anchor="middle"`
- Centered badge text: always `text-anchor="middle"` at column center-x

---

## Pattern: `two-column-comparison`

**Structure:** Vertical divider splits canvas into two equal columns. Each column has a top badge, a content box, a downward arrow, and a response box. A bottom label spans the full width.

**Use for:** Before/after, vague/specific, old/new side-by-side comparisons.

### Column layout procedure

For 2 equal columns on a 1440-wide canvas:
1. Place divider at x=720
2. Left column: x_start=60, width=620, center_x=370
3. Right column: x_start=760, width=620, center_x=1070
4. Badge width=380, centered in each column (x_start + 120)

### Vertical element order
Badge → content/prompt box → vertical arrow → response box → column label → bottom label

Apply the vertical rhythm rules above. The prompt box height adjusts to fit its text (1–2 lines typically). The response box height adjusts to fit 2–4 items. Both columns share the same y positions for every element.

---

## Pattern: `two-row-diagram`

**Structure:** Two horizontal rows stacked vertically. Each row: left box → horizontal arrow → right box. A bottom label spans the full width.

**Use for:** Showing a parallel contrast in outcomes (e.g. vague→broad output, specific→focused output).

### Layout procedure

1. Left box: x=80, width=480 (right edge=560); right box: x=660, width=700 (right edge=1360)
2. Center of left box: x=320; center of right box: x=1010
3. Row 1 top: y≈110 (near top of SVG area with header)
4. Standard row box height: 130px (enough for a title + one subtitle line)
5. Row gap (bottom of row 1 to top of row 2): 80–100px — increase if content needs more vertical room
6. Row 2 top: row1_top + row1_height + row_gap
7. Horizontal arrow: from right edge of left box to left edge of right box, centered vertically on the box height
8. Bottom label: y = row2_bottom + 60

### Text within each row box
- Title (role label, size=30, weight=600): baseline at box_top + 55
- Subtitle (example text, size=24): baseline at box_top + 93

---

## Pattern: `horizontal-flow-3`

**Structure:** Three equal step boxes with numbered circles, connected left-to-right by horizontal arrows. A bottom label spans the full width.

**Use for:** 3-stage processes, before/during/after progressions, step sequences.

### Layout procedure

For 3 equal boxes on a 1440-wide canvas with 100px inter-box gaps and side margins of 60px (left) / 70px (right):
- box_width = (1440 − 60 − 70 − 2×100) / 3 = 370
- Box x positions: 60, 530, 1000
- Box center_x values: 245, 715, 1185
- Box top: y≈130; height≈260 (accommodates circle + 2 subtitle lines + a note line)

### Element order within each box (top to bottom)
1. Numbered circle: r=28, cy = box_top + 42; number text baseline = cy + 10
2. Step title: y = circle_cy + 56, size=32, weight=600
3. Subtitle line 1: y = title_y + 37, size=24
4. Subtitle line 2: y = subtitle1_y + 30, size=24
5. Note/example (italic): y = subtitle2_y + 63, size=21

### Arrow
Horizontal arrow from right edge of box N to left edge of box N+1, centered vertically on the box. Arrow span = 100px (the inter-box gap).

---

## Pattern: `annotated-chat-exchange`

**Structure:** Two rounds of chat stacked vertically. Each round: user bubble (right-aligned) above AI bubble (left-aligned), with an annotation badge to the right of the AI bubble. Rounds separated by a downward arrow and a transition label.

**Use for:** Prompt iteration — showing how a revised prompt produces better output.

### Layout procedure

**Horizontal positioning:**
- AI bubbles: left-aligned, x=100, width=560
- User bubbles: right-aligned — x = 1440 − 60 − bubble_width; use width 460–600 depending on text length
- Annotation badges: right-aligned alongside AI bubble, x≈700; width sized to fit label text

**Vertical layout for each exchange:**
1. User bubble: height fits 1–2 lines, minimum 90px
2. Gap: 28px
3. AI bubble: height fits 1–3 lines, minimum 100px
4. Annotation badge: vertically centered on AI bubble, positioned to the right

**Between exchange 1 and exchange 2:**
- Downward arrow: centered on canvas (x=720), 54px total
- Transition label: x=740, alongside arrow, size=21, italic — describes what changed

**Annotation colors:**
- Problem / missing context: fill=#FFF3F1, stroke=#E02D16, text=#E02D16
- Improvement / better output: fill=#EAF7EE, stroke=#3EA33E, text=#3EA33E

**Starting y for exchange 1:** ≈30px from SVG top. Exchange 2 starts after exchange 1's AI bubble bottom + arrow + gap.
