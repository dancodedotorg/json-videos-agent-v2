"""
Update pipeline fields in a script.json file.

Usage:
  python update-pipeline.py <script.json> key1=value1 [key2=value2 ...]

Examples:
  python update-pipeline.py videos/my-video/script.json html=complete html_mode=ai_images
  python update-pipeline.py videos/my-video/script.json audio=pending audio_tags=pending

Exit codes:
  0  success
  1  error (file not found, invalid JSON, bad arguments)
"""

import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 3:
        print(
            "Usage: update-pipeline.py <script.json> key=value [key=value ...]",
            file=sys.stderr,
        )
        sys.exit(1)

    script_path = Path(sys.argv[1])
    if not script_path.exists():
        print(f"Error: {script_path} not found", file=sys.stderr)
        sys.exit(1)

    updates = {}
    for arg in sys.argv[2:]:
        if "=" not in arg:
            print(f"Error: invalid argument '{arg}' — expected key=value", file=sys.stderr)
            sys.exit(1)
        key, _, value = arg.partition("=")
        if not key:
            print(f"Error: empty key in '{arg}'", file=sys.stderr)
            sys.exit(1)
        updates[key] = value

    try:
        with open(script_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: could not parse {script_path}: {e}", file=sys.stderr)
        sys.exit(1)

    if "pipeline" not in data:
        print(f"Error: no 'pipeline' key in {script_path}", file=sys.stderr)
        sys.exit(1)

    for key, value in updates.items():
        data["pipeline"][key] = value
        print(f"  pipeline.{key} = {value!r}")

    tmp = script_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(script_path)

    print(f"Updated {script_path}")


if __name__ == "__main__":
    main()
