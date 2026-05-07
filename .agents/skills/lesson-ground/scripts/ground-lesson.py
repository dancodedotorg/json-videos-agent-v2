"""Fetch all source materials for a single lesson.

Expects a clean, pre-validated sources.csv. All ambiguity (typos, REVIEW rows,
re-fetch confirmation) must be resolved by the caller before invoking this script.

Usage:
    python ground-lesson.py <unit-slug> <lesson-slug> [--force] [--dry-run]

Exit codes:
    0  All sources fetched successfully
    1  Fatal error (missing file, unknown type, fetch failure, etc.)
    2  Already grounded and --force not passed
"""

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TOOLS_DIR = Path(__file__).parent
GOOGLE_FETCH = TOOLS_DIR / "google-fetch.py"

# Resolve repo root from __file__ location (cwd-independent)
# ground-lesson.py -> scripts -> lesson-ground -> skills -> .agents -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[4]

KNOWN_TYPES = {
    "google_slides",
    "google_doc",
    "level_summary",
    "google_drive_file",
    "objective",
    "vocabulary",
}

FETCHABLE_TYPES = {"google_slides", "google_doc", "level_summary", "google_drive_file"}
LOCAL_TYPES = {"objective", "vocabulary"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def die(msg: str) -> None:
    print(f"x {msg}", file=sys.stderr)
    sys.exit(1)


def load_sources_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return [{k.strip(): v.strip() for k, v in row.items()}
                for row in csv.DictReader(f)]


def run_google_fetch(fetch_type: str, value: str, source_dir: Path, dry_run: bool) -> bool:
    cmd = [sys.executable, str(GOOGLE_FETCH), fetch_type, value, str(source_dir)]
    if dry_run:
        print(f"   [dry-run] {' '.join(cmd)}")
        return True
    return subprocess.run(cmd).returncode == 0


def write_bullet_file(path: Path, items: list[str], dry_run: bool) -> None:
    content = "\n".join(f"- {item}" for item in items) + "\n"
    if dry_run:
        print(f"   [dry-run] write {path} ({len(items)} items)")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def ground_lesson(
    unit: str,
    lesson_slug: str,
    base_dir: Path,
    force: bool = False,
    dry_run: bool = False,
) -> int:
    lesson_dir = base_dir / "generation" / "units" / unit / "lessons" / lesson_slug
    source_dir = lesson_dir / "source"
    state_path = lesson_dir / "lesson-state.json"
    csv_path   = lesson_dir / "sources.csv"

    # ------------------------------------------------------------------
    # Step 1: Check existing grounding
    # ------------------------------------------------------------------
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("grounding") == "complete" and not force:
            print(f"Already grounded on {state.get('grounded_at', 'unknown')}. Pass --force to re-fetch.")
            return 2

    # ------------------------------------------------------------------
    # Step 2: Load sources.csv -- fail hard on anything unexpected
    # ------------------------------------------------------------------
    if not csv_path.exists():
        die(f"sources.csv not found: {csv_path}")

    rows = load_sources_csv(csv_path)
    if not rows:
        die(f"sources.csv is empty: {csv_path}")

    for row in rows:
        t = row.get("type", "")
        if t not in KNOWN_TYPES:
            die(f'Unknown type "{t}" in row "{row.get("description", "")}". Fix sources.csv before running.')
        if t in FETCHABLE_TYPES and not row.get("value", ""):
            die(f'Empty value for fetchable type "{t}" in row "{row.get("description", "")}".')

    # ------------------------------------------------------------------
    # Step 3: Fetch
    # ------------------------------------------------------------------
    if not dry_run:
        source_dir.mkdir(parents=True, exist_ok=True)

    fetch_count = 0
    errors: list[str] = []
    objectives: list[str] = []
    vocabulary: list[str] = []

    for row in rows:
        rtype = row["type"]
        value = row.get("value", "")
        desc  = row.get("description", value)

        if rtype in FETCHABLE_TYPES:
            print(f"   Fetching [{rtype}] {desc} ...")
            if run_google_fetch(rtype, value, source_dir, dry_run):
                fetch_count += 1
            else:
                errors.append(f"[{rtype}] {desc}")

        elif rtype == "objective":
            objectives.append(value)

        elif rtype == "vocabulary":
            vocabulary.append(value)

    if objectives:
        write_bullet_file(source_dir / "objectives.md", objectives, dry_run)
        print(f"   Wrote {len(objectives)} objective(s) -> objectives.md")
        fetch_count += 1

    if vocabulary:
        write_bullet_file(source_dir / "vocabulary.md", vocabulary, dry_run)
        print(f"   Wrote {len(vocabulary)} vocabulary item(s) -> vocabulary.md")
        fetch_count += 1

    # ------------------------------------------------------------------
    # Step 4: Write lesson-state.json
    # ------------------------------------------------------------------
    state = {
        "grounding": "complete" if not errors else "partial",
        "grounded_at": datetime.now(timezone.utc).isoformat(),
        "sources_fetched": fetch_count,
        "errors": errors,
    }
    if not dry_run:
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    return 0 if not errors else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("unit",    help="Unit slug (e.g. aif1-v2-2025)")
    parser.add_argument("lesson",  help="Lesson slug (e.g. lesson-3-the-ais-brain)")
    parser.add_argument("--force",   action="store_true", help="Re-fetch even if already grounded")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing")
    parser.add_argument("--base-dir", default=str(_REPO_ROOT), help="Repo root (default: auto-detected from script location)")
    args = parser.parse_args()

    code = ground_lesson(
        unit=args.unit,
        lesson_slug=args.lesson,
        base_dir=Path(args.base_dir).resolve(),
        force=args.force,
        dry_run=args.dry_run,
    )
    sys.exit(code)


if __name__ == "__main__":
    main()
