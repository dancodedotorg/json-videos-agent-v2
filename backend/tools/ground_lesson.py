"""Ensure a lesson's source materials are grounded for video generation."""

import json
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.request

from google.adk.tools.tool_context import ToolContext

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent

INIT_LESSON_SCRIPT = (
    PROJECT_ROOT / ".agents" / "skills" / "lesson-init" / "scripts" / "init_lesson.py"
)
GROUND_LESSON_SCRIPT = (
    PROJECT_ROOT / ".agents" / "skills" / "lesson-ground" / "scripts" / "ground-lesson.py"
)


# ---------------------------------------------------------------------------
# Slug / resolution helpers
# ---------------------------------------------------------------------------

def _canonical_slug(title: str) -> str:
    """Convert "Lesson 2: Beyond Words" → "lesson-2-beyond-words"."""
    def slugify(text: str) -> str:
        text = re.sub(r"[^a-z0-9\s-]", "", text.lower().strip())
        return re.sub(r"[\s-]+", "-", text).strip("-")

    m = re.match(r"lesson\s+(\d+)\s*:\s*(.+)", title, re.IGNORECASE)
    if m:
        return f"lesson-{m.group(1)}-{slugify(m.group(2))}"
    return slugify(title)


def _lesson_number_from_title(title: str) -> int | None:
    m = re.match(r"lesson\s+(\d+)", title, re.IGNORECASE)
    return int(m.group(1)) if m else None


def _matches_input(lesson_input: str, title: str, slug: str) -> bool:
    """Return True if lesson_input (number, slug prefix, or name fragment) matches."""
    inp = lesson_input.strip()
    # Bare number or "lesson-N" / "lesson N"
    num_m = re.match(r"^(?:lesson[-\s]?)?(\d+)$", inp, re.IGNORECASE)
    if num_m:
        return _lesson_number_from_title(title) == int(num_m.group(1))
    if slug == inp.lower():
        return True
    if slug.startswith(inp.lower().replace(" ", "-")):
        return True
    if inp.lower() in title.lower():
        return True
    return False


def _resolve_lesson(
    unit: str,
    lesson: str,
    units_root: pathlib.Path,
) -> tuple[str | None, int | None, str | None]:
    """Resolve a lesson identifier to (slug, lesson_id, error_message).

    lesson_id may be None when the folder already exists with sources.csv
    (we don't need the ID to run grounding in that case).
    Returns (None, None, error_str) on failure.
    """
    lessons_dir = units_root / unit / "lessons"
    found_slug: str | None = None

    # Step 1: scan existing lesson folders
    if lessons_dir.exists():
        matches = [
            d.name
            for d in lessons_dir.iterdir()
            if d.is_dir() and _matches_input(lesson, d.name, d.name)
        ]
        if len(matches) == 1:
            found_slug = matches[0]
        elif len(matches) > 1:
            return (
                None,
                None,
                f"Ambiguous lesson '{lesson}' matches multiple folders: "
                f"{', '.join(sorted(matches))}. Please be more specific.",
            )

    # Step 2: look up lesson_id from unit.json
    unit_json_path = units_root / unit / "unit.json"
    if unit_json_path.exists():
        with open(unit_json_path, encoding="utf-8") as f:
            data = json.load(f)
        for entry in data.get("lessons", []):
            title = entry.get("title", "")
            slug = _canonical_slug(title)
            if _matches_input(lesson, title, slug):
                lesson_id = entry.get("id")
                return found_slug or slug, lesson_id, None
        # Folder found but lesson not in unit.json — return slug without ID
        if found_slug:
            return found_slug, None, None

    # Step 3: fall back to Code.org API
    url = f"https://studio.code.org/s/{unit}/lessons"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            api_lessons = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        if found_slug:
            return found_slug, None, None
        return (
            None,
            None,
            f"Could not resolve lesson '{lesson}': unit.json not found and "
            f"Code.org API request failed ({exc}).",
        )

    for entry in api_lessons:
        title = entry.get("name", "")
        slug = _canonical_slug(title)
        if _matches_input(lesson, title, slug):
            lesson_id = entry.get("id")
            return found_slug or slug, lesson_id, None

    if found_slug:
        return found_slug, None, None

    return (
        None,
        None,
        f"Lesson '{lesson}' not found in unit '{unit}' "
        "(checked existing folders, unit.json, and Code.org API).",
    )


# ---------------------------------------------------------------------------
# Grounding
# ---------------------------------------------------------------------------

def _run_grounding(unit: str, slug: str, state_path: pathlib.Path) -> dict:
    """Invoke ground-lesson.py and read lesson-state.json for the result."""
    result = subprocess.run(
        [
            sys.executable,
            str(GROUND_LESSON_SCRIPT),
            unit,
            slug,
            "--base-dir",
            str(PROJECT_ROOT),
        ],
        capture_output=True,
        text=True,
    )
    # Exit code 2 = already grounded (race / concurrent call)
    if result.returncode == 2:
        return {"status": "already_complete", "lesson_slug": slug, "sources_fetched": 0, "errors": []}

    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        return {
            "status": state.get("grounding", "error"),
            "lesson_slug": slug,
            "sources_fetched": state.get("sources_fetched", 0),
            "errors": state.get("errors", []),
        }

    return {
        "status": "error",
        "lesson_slug": slug,
        "sources_fetched": 0,
        "errors": [result.stderr.strip() or "ground-lesson.py failed without writing lesson-state.json"],
    }


# ---------------------------------------------------------------------------
# Main tool
# ---------------------------------------------------------------------------

async def ground_lesson(unit: str, lesson: str, tool_context: ToolContext) -> dict:
    """Ensure a lesson is grounded (source materials fetched) for video generation.

    Idempotent: returns immediately if already grounded. Otherwise resolves the
    lesson slug, generates sources.csv if needed, and on a subsequent call runs
    the actual grounding fetch.

    The tool is intentionally two-phase so the agent can show the user the
    proposed source list and get confirmation before the expensive network fetch:
    - First call (sources.csv missing): generates it and returns
      'sources_csv_generated' or 'needs_sources_csv' without running grounding.
    - Second call (sources.csv on disk): runs ground-lesson.py and returns
      'complete' or 'partial'.

    Args:
        unit: Unit slug (e.g. 'aif1-v2-2025') or 'standalone'
        lesson: Lesson number ('2'), slug prefix, or full slug.
                For standalone units this is the slug the user chose.

    Returns:
        dict with keys: status, lesson_slug, sources_fetched, errors

        status values:
          'already_complete'       lesson was already grounded, no action taken
          'sources_csv_generated'  sources.csv built from curriculum data;
                                   agent should review with user, then call again
          'needs_sources_csv'      standalone lesson has no curriculum data;
                                   agent must gather materials and write sources.csv,
                                   then call again
          'complete'               grounding finished successfully
          'partial'                grounding ran but some sources failed (see errors)
          'error'                  could not proceed (see errors)
    """
    units_root = PROJECT_ROOT / "generation" / "units"

    # -------------------------------------------------------------------------
    # Standalone unit — lesson parameter IS the final slug (user-chosen)
    # -------------------------------------------------------------------------
    if unit == "standalone":
        slug = lesson
        state_path = units_root / unit / "lessons" / slug / "lesson-state.json"
        csv_path = units_root / unit / "lessons" / slug / "sources.csv"

        if state_path.exists():
            state = json.loads(state_path.read_text(encoding="utf-8"))
            if state.get("grounding") == "complete":
                return {
                    "status": "already_complete",
                    "lesson_slug": slug,
                    "sources_fetched": state.get("sources_fetched", 0),
                    "errors": [],
                }

        if not csv_path.exists():
            return {
                "status": "needs_sources_csv",
                "lesson_slug": slug,
                "sources_fetched": 0,
                "errors": [],
            }

        return _run_grounding(unit, slug, state_path)

    # -------------------------------------------------------------------------
    # Code.org unit — resolve slug and lesson_id from input
    # -------------------------------------------------------------------------
    slug, lesson_id, err = _resolve_lesson(unit, lesson, units_root)
    if err:
        return {"status": "error", "lesson_slug": None, "sources_fetched": 0, "errors": [err]}

    state_path = units_root / unit / "lessons" / slug / "lesson-state.json"
    csv_path = units_root / unit / "lessons" / slug / "sources.csv"

    # Already grounded — fast path
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("grounding") == "complete":
            return {
                "status": "already_complete",
                "lesson_slug": slug,
                "sources_fetched": state.get("sources_fetched", 0),
                "errors": [],
            }

    # Phase 1: sources.csv missing — generate it and return for review
    if not csv_path.exists():
        if not lesson_id:
            return {
                "status": "error",
                "lesson_slug": slug,
                "sources_fetched": 0,
                "errors": [
                    "sources.csv is missing and the lesson ID could not be determined. "
                    "Provide the exact lesson slug or run /lesson-init first."
                ],
            }
        result = subprocess.run(
            [sys.executable, str(INIT_LESSON_SCRIPT), unit, str(lesson_id)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return {
                "status": "error",
                "lesson_slug": slug,
                "sources_fetched": 0,
                "errors": [result.stderr.strip() or result.stdout.strip()],
            }
        # init_lesson.py derives its own slug from the title; verify csv_path exists.
        # If the slug differed slightly, scan to find the newly created folder.
        if not csv_path.exists():
            lessons_dir = units_root / unit / "lessons"
            candidates = [
                d.name
                for d in lessons_dir.iterdir()
                if d.is_dir()
                and _matches_input(lesson, d.name, d.name)
                and (d / "sources.csv").exists()
            ]
            if len(candidates) == 1:
                slug = candidates[0]
                csv_path = units_root / unit / "lessons" / slug / "sources.csv"
                state_path = units_root / unit / "lessons" / slug / "lesson-state.json"
            else:
                return {
                    "status": "error",
                    "lesson_slug": slug,
                    "sources_fetched": 0,
                    "errors": ["init_lesson.py ran but sources.csv was not found afterward."],
                }

        return {
            "status": "sources_csv_generated",
            "lesson_slug": slug,
            "sources_fetched": 0,
            "errors": [],
        }

    # Phase 2: sources.csv confirmed on disk — run grounding
    return _run_grounding(unit, slug, state_path)
