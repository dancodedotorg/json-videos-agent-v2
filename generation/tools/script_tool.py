"""
script_tool.py — Targeted read/write/view utility for script.json files.

Avoids loading large JSON into LLM context for simple field access, and provides
a stripped "view" that omits large per-scene fields (html, elevenlabs, gemini).

COMMANDS
--------
  get  <script.json> <path>              Print a specific value by dot-notation path
  set  <script.json> <path> <value>      Set a scalar value by dot-notation path (atomic write)
  view <script.json> [--omit f1,f2,...]  Pretty-print with large scene fields replaced by "<omitted>"

PATH SYNTAX
-----------
  pipeline.script           → data["pipeline"]["script"]
  scenes.2.speech           → data["scenes"][2]["speech"]
  tts.provider              → data["tts"]["provider"]

  Integer segments are treated as list indices.

VALUE COERCION (set command)
----------------------------
  "true" / "false"  → bool
  Pure integers     → int
  Everything else   → string

DEFAULT --omit FIELDS
---------------------
  html, elevenlabs, gemini

EXAMPLES
--------
  python generation/tools/script_tool.py get   script.json pipeline.script
  python generation/tools/script_tool.py set   script.json pipeline.audio complete
  python generation/tools/script_tool.py view  script.json
  python generation/tools/script_tool.py view  script.json --omit html
  python generation/tools/script_tool.py view  script.json --omit html,elevenlabs,gemini

EXIT CODES
----------
  0  Success
  1  Path not found, type error, or I/O error
  2  JSON parse error
"""

import argparse
import json
import sys
from pathlib import Path


# ── Path resolution ────────────────────────────────────────────────────────────

def resolve_path(data, path: str):
    """Walk a dot-notation path into a nested dict/list and return the node."""
    parts = path.split(".")
    node = data
    for part in parts:
        try:
            key = int(part) if isinstance(node, list) else part
            node = node[key]
        except (KeyError, IndexError, TypeError) as e:
            raise KeyError(f"path segment '{part}' not found: {e}") from e
    return node


def set_path(data, path: str, value):
    """Set a leaf value at a dot-notation path. Raises KeyError if parent path is missing."""
    parts = path.split(".")
    node = data
    for part in parts[:-1]:
        key = int(part) if isinstance(node, list) else part
        node = node[key]
    last = parts[-1]
    key = int(last) if isinstance(node, list) else last
    node[key] = value


def coerce_value(raw: str):
    """Coerce a CLI string to bool, int, or str."""
    if raw.lower() == "true":
        return True
    if raw.lower() == "false":
        return False
    try:
        return int(raw)
    except ValueError:
        return raw


# ── Atomic write ───────────────────────────────────────────────────────────────

def atomic_write(path: Path, data: dict):
    """Write data to path using a temp file + rename for crash safety."""
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


# ── Commands ───────────────────────────────────────────────────────────────────

def cmd_get(script_path: Path, path: str):
    try:
        data = json.loads(script_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: JSON parse error: {e}", file=sys.stderr)
        sys.exit(2)

    try:
        value = resolve_path(data, path)
    except KeyError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if isinstance(value, (dict, list)):
        print(json.dumps(value, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(value))


def cmd_set(script_path: Path, path: str, raw_value: str):
    try:
        data = json.loads(script_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: JSON parse error: {e}", file=sys.stderr)
        sys.exit(2)

    value = coerce_value(raw_value)

    try:
        set_path(data, path, value)
    except (KeyError, IndexError, TypeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        atomic_write(script_path, data)
    except OSError as e:
        print(f"ERROR: could not write {script_path}: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Set {path} = {json.dumps(value)}")


def cmd_view(script_path: Path, omit_fields: list[str]):
    try:
        data = json.loads(script_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: JSON parse error: {e}", file=sys.stderr)
        sys.exit(2)

    omit_set = set(omit_fields)
    if omit_set and "scenes" in data:
        import copy
        data = copy.deepcopy(data)
        for scene in data["scenes"]:
            for field in omit_set:
                if field in scene:
                    scene[field] = "<omitted>"

    print(json.dumps(data, indent=2, ensure_ascii=False))


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Targeted read/write/view utility for script.json files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python script_tool.py get  script.json pipeline.script
  python script_tool.py set  script.json pipeline.audio complete
  python script_tool.py view script.json
  python script_tool.py view script.json --omit html,elevenlabs,gemini
        """,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # get
    p_get = subparsers.add_parser("get", help="Print a value by dot-notation path")
    p_get.add_argument("script", help="Path to script.json")
    p_get.add_argument("path", help="Dot-notation path (e.g. pipeline.script, scenes.2.speech)")

    # set
    p_set = subparsers.add_parser("set", help="Set a scalar value by dot-notation path")
    p_set.add_argument("script", help="Path to script.json")
    p_set.add_argument("path", help="Dot-notation path")
    p_set.add_argument("value", help="Value to set (auto-coerced: true/false → bool, integers → int)")

    # view
    p_view = subparsers.add_parser("view", help="Pretty-print with large scene fields omitted")
    p_view.add_argument("script", help="Path to script.json")
    p_view.add_argument(
        "--omit",
        default="html,elevenlabs,gemini",
        help="Comma-separated scene fields to replace with '<omitted>' (default: html,elevenlabs,gemini)",
    )

    args = parser.parse_args()

    script_path = Path(args.script)
    if not script_path.exists():
        print(f"ERROR: file not found: {script_path}", file=sys.stderr)
        sys.exit(1)

    if args.command == "get":
        cmd_get(script_path, args.path)
    elif args.command == "set":
        cmd_set(script_path, args.path, args.value)
    elif args.command == "view":
        omit_fields = [f.strip() for f in args.omit.split(",") if f.strip()]
        cmd_view(script_path, omit_fields)


if __name__ == "__main__":
    main()
