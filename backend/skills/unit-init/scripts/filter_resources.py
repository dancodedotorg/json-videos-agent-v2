"""
filter_resources.py — Filter a Code.org unit resources JSON into a leaner format.

Usage:
    python filter_resources.py <resources_file> [lessons_file]

Arguments:
    resources_file  Path to the resources JSON (e.g. resources.json).
                    Must match the shape produced by the Code.org curriculum API,
                    with a top-level "unit_summary.lessons" array.

    lessons_file    (Optional) Path to a lessons JSON array (e.g. lessons.json).
                    Each element must have "id" and "name" fields. When provided,
                    lesson IDs are looked up by matching "name" against the lesson
                    title and added as an "id" field on each lesson object.

Output:
    A new file named `unit.json` in the same directory as <resources_file>.

    The output contains a single top-level object:
        {
          "lessons": [
            {
              "id": <int, only present when lessons_file is given and a match is found>,
              "key": <str>,
              "title": <str>,
              "resources": [
                { "id": <int>, "key": <str>, "url": <str> },
                ...
              ],
              "vocabularies": [...],
              "objectives": [...]
            },
            ...
          ]
        }

    Resources are merged from Student and Teacher audiences into a single list,
    and only entries with type "Activity Guide", "Resource", or "Slides" are kept.

Example:
    python filter_resources.py resource_page_experiments/resources.json resource_page_experiments/lessons.json
"""

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_REPO_ROOT / "generation" / "tools"))
from text_utils import normalize_data

ALLOWED_RESOURCE_TYPES = {"Activity Guide", "Resource", "Slides"}


def load_json(path: Path) -> object:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_id_lookup(lessons_data: list) -> dict:
    """Return a dict mapping lesson name → id from the lessons JSON array."""
    return {entry["name"]: entry["id"] for entry in lessons_data}


def filter_resources(raw_resources: dict) -> list:
    """Merge Student+Teacher resource lists and keep only allowed types with minimal fields."""
    merged = []
    seen_ids = set()
    for audience_list in raw_resources.values():
        for resource in audience_list:
            if resource.get("type") not in ALLOWED_RESOURCE_TYPES:
                continue
            rid = resource.get("id")
            if rid in seen_ids:
                continue
            seen_ids.add(rid)
            merged.append({
                "id": rid,
                "key": resource.get("key"),
                "url": resource.get("url"),
            })
    return merged


def filter_lesson(lesson: dict, id_lookup: dict | None) -> dict:
    result = {
        "key": lesson.get("key"),
        "title": lesson.get("title"),
        "resources": filter_resources(lesson.get("resources", {})),
        "vocabularies": lesson.get("vocabularies", []),
        "objectives": lesson.get("objectives", []),
    }

    if id_lookup is not None:
        title = lesson.get("title") or lesson.get("key", "")
        lesson_id = id_lookup.get(title)
        if lesson_id is not None:
            result = {"id": lesson_id, **result}

    return result


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    resources_path = Path(sys.argv[1])
    lessons_path = Path(sys.argv[2]) if len(sys.argv) >= 3 else None

    resources_data = load_json(resources_path)
    lessons_data = load_json(lessons_path) if lessons_path else None
    id_lookup = build_id_lookup(lessons_data) if lessons_data else None

    raw_lessons = resources_data.get("unit_summary", {}).get("lessons", [])
    filtered_lessons = [filter_lesson(lesson, id_lookup) for lesson in raw_lessons]

    output_path = resources_path.parent / "unit.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(normalize_data({"lessons": filtered_lessons}), f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(filtered_lessons)} lessons → {output_path}")


if __name__ == "__main__":
    main()
