#!/usr/bin/env python3
"""Ground all lessons in a unit.

Walks the folder structure:
    generation/units/<unit>/lessons/<lesson>/sources.csv

and runs ground-lesson.py for each lesson that has a sources.csv.

Usage:
    python ground-all.py <unit-slug>           # ground all lessons in one unit
    python ground-all.py <unit-slug> --force   # re-fetch already-grounded lessons
    python ground-all.py <unit-slug> --dry-run

Exit codes:
    0  All lessons succeeded (or were already grounded)
    1  One or more lessons failed
"""

import argparse
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
GROUND_LESSON = _REPO_ROOT / ".claude" / "skills" / "lesson-ground" / "scripts" / "ground-lesson.py"


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def discover_lessons(unit_dir: Path) -> list[Path]:
    """Return sorted list of lesson directories that contain a sources.csv."""
    lessons_root = unit_dir / "lessons"
    if not lessons_root.is_dir():
        return []
    return sorted(
        p for p in lessons_root.iterdir()
        if p.is_dir() and (p / "sources.csv").exists()
    )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_ground_lesson(unit: str, lesson_slug: str, base_dir: Path, force: bool, dry_run: bool) -> int:
    cmd = [sys.executable, str(GROUND_LESSON), unit, lesson_slug, "--base-dir", str(base_dir)]
    if force:
        cmd.append("--force")
    if dry_run:
        cmd.append("--dry-run")
    return subprocess.run(cmd).returncode


def run_all(
    unit_slug: str,
    base_dir: Path,
    force: bool = False,
    dry_run: bool = False,
) -> int:
    unit_dir = base_dir / "generation" / "units" / unit_slug

    if not unit_dir.is_dir():
        print(f"x Unit directory not found: {unit_dir}", file=sys.stderr)
        return 1

    lesson_dirs = discover_lessons(unit_dir)

    if not lesson_dirs:
        print(f"Warning: No lessons with sources.csv found in: {unit_dir}", file=sys.stderr)
        return 0

    print(f"Found {len(lesson_dirs)} lesson(s) in {unit_slug}")

    results: list[tuple[str, int]] = []

    for lesson_dir in lesson_dirs:
        lesson_slug = lesson_dir.name
        print(f"\n{'='*60}")
        print(f"  {unit_slug} / {lesson_slug}")
        print(f"{'='*60}")

        code = run_ground_lesson(unit_slug, lesson_slug, base_dir, force, dry_run)
        results.append((lesson_slug, code))

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print(f"\n{'='*60}")
    print(f"Summary - {unit_slug}")
    print(f"{'='*60}")

    failed = 0
    for lesson_slug, code in results:
        if code == 0:
            icon = "ok"
        elif code == 2:
            icon = "skip"
        else:
            icon = "FAIL"
            failed += 1
        print(f"  [{icon}]  {lesson_slug}")

    skipped = sum(1 for _, c in results if c == 2)
    succeeded = sum(1 for _, c in results if c == 0)

    print(f"\n  Total   : {len(results)}")
    print(f"  Success : {succeeded}")
    print(f"  Skipped : {skipped}  (already grounded - use --force to re-fetch)")
    print(f"  Failed  : {failed}")

    return 0 if failed == 0 else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("unit", help="Unit slug (e.g. aif1-v2-2025)")
    parser.add_argument("--force",    action="store_true", help="Re-fetch already-grounded lessons")
    parser.add_argument("--dry-run",  action="store_true", help="Print commands without executing")
    parser.add_argument("--base-dir", default=".",         help="Repo root (default: cwd)")
    args = parser.parse_args()

    sys.exit(run_all(
        unit_slug=args.unit,
        base_dir=Path(args.base_dir).resolve(),
        force=args.force,
        dry_run=args.dry_run,
    ))


if __name__ == "__main__":
    main()
