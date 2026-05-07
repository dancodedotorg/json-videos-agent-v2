"""
init_lesson.py — Initialize a lesson folder within a curriculum unit.

Usage:
    python generation/tools/init_lesson.py <unit-slug> <lesson-id>

Arguments:
    unit-slug   The unit slug (e.g. aif1-v2-2025)
    lesson-id   The numeric lesson ID from unit.json (e.g. 9520955)

Looks up the lesson by ID in unit.json, derives the canonical folder slug from its
title, creates the lesson folder structure, and writes sources.csv.

Exit codes:
    0  success
    1  usage error or unit.json not found
    2  lesson ID not found in unit.json
"""

import csv
import json
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_REPO_ROOT / "generation" / "tools"))
from paths import unit_json, lesson_sources_csv, lesson_source, lesson_videos_root
from text_utils import normalize_data


def canonical_slug(title: str) -> str:
    """Convert "Lesson 2: Beyond Words" → "lesson-2-beyond-words"."""
    def slugify(text: str) -> str:
        text = re.sub(r"[^a-z0-9\s-]", "", text.lower().strip())
        return re.sub(r"[\s-]+", "-", text).strip("-")

    m = re.match(r"lesson\s+(\d+)\s*:\s*(.+)", title, re.IGNORECASE)
    if m:
        return f"lesson-{m.group(1)}-{slugify(m.group(2))}"
    return slugify(title)


def url_to_type(url: str) -> str:
    if "/presentation/" in url:
        return "google_slides"
    if "/document/" in url:
        return "google_doc"
    return "google_drive_file"


def key_to_description(key: str) -> str:
    return key.replace("_", " ").title()


def build_sources_rows(lesson: dict) -> tuple:
    """Return (rows, drive_file_warnings). rows are [description, type, value] lists."""
    rows = []
    warnings = []

    for resource in lesson.get("resources", []):
        url = resource.get("url", "")
        rtype = url_to_type(url)
        desc = key_to_description(resource.get("key", "resource"))
        if rtype == "google_drive_file":
            desc = f"REVIEW: {desc}"
            warnings.append((desc, url))
        rows.append([desc, rtype, url])

    if lesson.get("id"):
        rows.append(["Lesson Levels", "level_summary", str(lesson["id"])])

    for vocab in lesson.get("vocabularies", []):
        word = vocab.get("word", "")
        definition = vocab.get("definition", "")
        rows.append([word, "vocabulary", f"{word}: {definition}"])

    for obj in lesson.get("objectives", []):
        full = obj.get("description", "")
        short = f"Objective: {full[:57]}..." if len(full) > 60 else f"Objective: {full}"
        rows.append([short, "objective", full])

    return rows, warnings


def write_csv(path: Path, rows: list):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["description", "type", "value"])
        writer.writerows(rows)


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    unit = sys.argv[1]
    try:
        lesson_id = int(sys.argv[2])
    except ValueError:
        print(f"Error: lesson-id must be an integer, got '{sys.argv[2]}'", file=sys.stderr)
        sys.exit(1)

    unit_json_path = unit_json(unit)
    if not unit_json_path.exists():
        print(f"Error: unit.json not found at {unit_json_path}", file=sys.stderr)
        sys.exit(1)

    with open(unit_json_path, encoding="utf-8") as f:
        data = json.load(f)

    lesson = next((l for l in data["lessons"] if l.get("id") == lesson_id), None)
    if lesson is None:
        print(f"Error: lesson id {lesson_id} not found in {unit_json_path}", file=sys.stderr)
        sys.exit(2)

    slug = canonical_slug(lesson["title"])

    lesson_source(unit, slug).mkdir(parents=True, exist_ok=True)
    lesson_videos_root(unit, slug).mkdir(parents=True, exist_ok=True)

    rows, warnings = build_sources_rows(normalize_data(lesson))
    write_csv(lesson_sources_csv(unit, slug), rows)

    if warnings:
        print("⚠️  The following resources need manual review in sources.csv:")
        for desc, url in warnings:
            print(f"  - {desc} ({url})")

    print(f"""✅ Lesson "{slug}" initialized in unit "{unit}".

  Location: generation/units/{unit}/lessons/{slug}/
  sources.csv: {len(rows)} rows auto-populated from unit.json

Next steps:
1. Review (and edit if needed) sources.csv
2. Run /lesson-ground {unit} {slug} to fetch source materials""")


if __name__ == "__main__":
    main()
