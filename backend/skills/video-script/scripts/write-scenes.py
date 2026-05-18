"""
Write a scenes array into a script.json and mark pipeline.script = complete.

Usage:
  python scripts/write-scenes.py SCRIPT_PATH SCENES_PATH

Arguments:
  SCRIPT_PATH   Path to the video's script.json (modified in place)
  SCENES_PATH   Path to a JSON file containing an array of scene objects

Exit codes: 0 success, 1 file not found or IO error, 2 invalid JSON
"""

import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 3:
        print("Usage: python scripts/write-scenes.py SCRIPT_PATH SCENES_PATH", file=sys.stderr)
        sys.exit(1)

    script_path = Path(sys.argv[1])
    scenes_path = Path(sys.argv[2])

    for path in (script_path, scenes_path):
        if not path.exists():
            print(f"Error: File not found: {path}", file=sys.stderr)
            sys.exit(1)

    try:
        script = json.loads(script_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {script_path}: {e}", file=sys.stderr)
        sys.exit(2)

    try:
        scenes = json.loads(scenes_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {scenes_path}: {e}", file=sys.stderr)
        sys.exit(2)

    if not isinstance(scenes, list):
        print(f"Error: {scenes_path} must contain a JSON array of scene objects", file=sys.stderr)
        sys.exit(2)

    script["scenes"] = scenes
    if "pipeline" not in script:
        script["pipeline"] = {}
    script["pipeline"]["script"] = "complete"

    tmp = script_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(script, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(script_path)
    print(f"Wrote {len(scenes)} scenes to {script_path} and set pipeline.script = complete")


if __name__ == "__main__":
    main()
