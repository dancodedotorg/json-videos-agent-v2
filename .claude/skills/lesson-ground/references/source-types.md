# Fetch types reference

Each row in `sources.csv` has a `type` field. This file lists what each type does and what files it produces in `source/`.

## google_slides

**Input:** Google Slides URL or presentation ID  
**Requires:** `GOOGLE_SERVICE_ACCOUNT_JSON` in `.env`

Outputs:
- `slide_01.png`, `slide_02.png`, ... — one PNG per slide (LARGE thumbnail)
- `slides_data.json` — array of `{index, slide_id, notes, png_base64: null}` (base64 stripped after saving PNGs)
- `slides_notes.pdf` — two-column PDF: slide image left, speaker notes right

## google_doc

**Input:** Google Doc URL or document ID  
**Requires:** Doc must be publicly accessible (no auth on export URL)

Outputs:
- `<doc-id>.pdf` — full document as PDF

## codeorg_markdown

**Input:** Code.org level name (e.g., `Unit3-Lesson5`)  
**Requires:** nothing (fetches from public GitHub)

Outputs:
- `<level-name>.md` — markdown content extracted from the `.external` config file

## level_summary

**Input:** Code.org lesson ID (numeric, e.g., `9520956`)  
**Requires:** nothing (fetches from public `studio.code.org` API)

Outputs:
- `lesson_<id>_levels.json` — filtered level data for these level types:
  - **Panels** — slide-style panels with image + text
  - **Aichat** — AI chat bot configuration and instructions
  - **FreeResponse** — open-ended writing prompt
  - **Multi** — multiple-choice question
  - **External** — markdown reading/reference page
- `panels_level_<id>.pdf` — one per Panels level: panel image left, text right
- `external_level_<id>.pdf` — one per External level: markdown rendered as HTML with images inlined

## google_drive_file

**Input:** Google Drive file URL or file ID  
**Requires:** manual download — cannot be auto-fetched

This type is always auto-flagged with `REVIEW:` in the description by `init_lesson.py` because Drive files cannot be fetched automatically. The user must download the file manually and either:
- Remove the row from `sources.csv` if the file is not needed, or
- Update the value with a local file path once downloaded

The `/lesson-ground` skill will prompt the user about each REVIEW row before running the fetch script.

## objective

**Input:** Plain text string describing a learning objective  
**Requires:** nothing (no network fetch)

Outputs:
- `source/objectives.md` — each objective appended as a bullet: `- <value>`

Use one row per objective. All objectives across all `objective` rows are collected into the same file.

## vocabulary

**Input:** Plain text string in `term: definition` format  
**Requires:** nothing (no network fetch)

Outputs:
- `source/vocabulary.md` — each term appended as a bullet: `- <value>`

Use one row per vocabulary term. All vocabulary rows are collected into the same file.
