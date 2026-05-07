"""
init_all_lessons.py — Initialize all lessons in a unit from its unit.json file.

Usage:
    python generation/tools/init_all_lessons.py <unit-slug>
"""

import json
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_REPO_ROOT / "generation" / "tools"))
from paths import unit_json


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    unit = sys.argv[1]
    unit_json_path = unit_json(unit)

    if not unit_json_path.exists():
        print(f"Error: unit.json not found at {unit_json_path}", file=sys.stderr)
        sys.exit(1)

    with open(unit_json_path, encoding="utf-8") as f:
        data = json.load(f)

    lessons = data.get("lessons", [])
    if not lessons:
        print("No lessons found in unit.json.")
        sys.exit(0)

    print(f"Initializing {len(lessons)} lessons for unit '{unit}'...\n")

    init_script = _REPO_ROOT / ".claude" / "skills" / "lesson-init" / "scripts" / "init_lesson.py"
    success, failure = 0, 0

    for lesson in lessons:
        lesson_id = lesson.get("id")
        title = lesson.get("title", "(untitled)")

        if lesson_id is None:
            print(f"⚠️  Skipping '{title}' — no id field.")
            failure += 1
            continue

        print(f"── Lesson {lesson_id}: {title}")
        result = subprocess.run(
            [sys.executable, str(init_script), unit, str(lesson_id)],
            capture_output=True,
            text=True,
        )
        print(result.stdout.strip())
        if result.returncode != 0:
            print(f"  ✗ Error: {result.stderr.strip()}", file=sys.stderr)
            failure += 1
        else:
            success += 1
        print()

    print(f"Done. {success} succeeded, {failure} failed.")
    if failure:
        sys.exit(1)


if __name__ == "__main__":
    main()