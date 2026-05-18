"""
fetch_unit.py — Fetch lesson list and unit resources from Code.org for a given unit slug.

Usage:
    python generation/tools/fetch_unit.py <unit-slug>

Saves:
    generation/units/<unit-slug>/lessons.json   — lesson ID + name array from the API
    generation/units/<unit-slug>/resources.json — unit rollup JSON from the resources page

Exit codes:
    0  both files saved successfully
    1  lessons fetch failed
    2  resources fetch failed (login required or data-unit-rollup not found)
"""

import html
import json
import sys
import urllib.request
import urllib.error
from html.parser import HTMLParser
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_REPO_ROOT / "generation" / "tools"))
from paths import unit_root, unit_lessons_json

BASE_URL = "https://studio.code.org"
TIMEOUT = 30


class UnitRollupParser(HTMLParser):
    """Extracts the JSON value of the first <script data-unit-rollup="..."> element."""

    def __init__(self):
        super().__init__()
        self.rollup_raw = None

    def handle_starttag(self, tag, attrs):
        if self.rollup_raw is not None:
            return
        if tag == "script":
            for name, value in attrs:
                if name == "data-unit-rollup":
                    self.rollup_raw = value
                    return


def fetch_json(url: str) -> tuple:
    """Return (parsed_json, final_url)."""
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8")), resp.url


def fetch_html(url: str) -> tuple:
    """Return (html_text, final_url)."""
    req = urllib.request.Request(url, headers={"Accept": "text/html,*/*"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8"), resp.url


def print_manual_fallback(slug: str):
    print(f"""
⚠️  Could not auto-fetch unit resources. Manual step required:

1. Open https://studio.code.org/s/{slug}/resources in your browser (must be logged in)
2. Run the Tampermonkey script at generation/tools/resources-rollup.user.js
3. Click "Copy" in the panel that appears
4. Save the copied JSON to: generation/units/{slug}/resources.json
5. Re-run /unit-init {slug}
""")


def fetch_lessons(slug: str) -> list:
    url = f"{BASE_URL}/s/{slug}/lessons"
    print(f"Fetching {url} ...")
    try:
        data, _ = fetch_json(url)
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} fetching lessons.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error fetching lessons: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(data, list):
        print(f"Unexpected lessons response (got {type(data).__name__}).", file=sys.stderr)
        sys.exit(1)

    return data


def fetch_resources(slug: str) -> dict:
    url = f"{BASE_URL}/s/{slug}/resources"
    print(f"Fetching {url} ...")
    try:
        html_text, final_url = fetch_html(url)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            print_manual_fallback(slug)
            sys.exit(2)
        print(f"HTTP {e.code} fetching resources.", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"Error fetching resources: {e}", file=sys.stderr)
        sys.exit(2)

    if "sign_in" in final_url or "login" in final_url.lower():
        print_manual_fallback(slug)
        sys.exit(2)

    parser = UnitRollupParser()
    parser.feed(html_text)

    if parser.rollup_raw is None:
        print_manual_fallback(slug)
        sys.exit(2)

    try:
        return json.loads(html.unescape(parser.rollup_raw))
    except json.JSONDecodeError as e:
        print(f"data-unit-rollup is not valid JSON: {e}", file=sys.stderr)
        sys.exit(2)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    slug = sys.argv[1]
    out_dir = unit_root(slug)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Lessons
    lessons = fetch_lessons(slug)
    lessons_path = unit_lessons_json(slug)
    with open(lessons_path, "w", encoding="utf-8") as f:
        json.dump(lessons, f, indent=2, ensure_ascii=False)

    print(f"\nFound {len(lessons)} lessons in \"{slug}\":")
    for lesson in lessons:
        print(f"  {lesson['id']} — {lesson['name']}")

    # Resources
    resources = fetch_resources(slug)
    resources_path = out_dir / "resources.json"
    with open(resources_path, "w", encoding="utf-8") as f:
        json.dump(resources, f, indent=2, ensure_ascii=False)

    print(f"\nSaved resources.json")


if __name__ == "__main__":
    main()
