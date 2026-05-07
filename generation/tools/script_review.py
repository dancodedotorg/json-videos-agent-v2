"""
Filter a JSON file to only include 'comment' and 'speech' fields from each scene.

Usage:
    python filter_json.py <input.json>

The filtered result is saved to <input>_script_review.json.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from text_utils import normalize_data


def filter_scenes(input_filename: str) -> None:
    with open(input_filename, "r") as f:
        data = json.load(f)
    
    data = normalize_data(data)
    filtered_scenes = []
    for scene in data.get("scenes", []):
        filtered_scenes.append({
            "comment": scene.get("comment", ""),
            "speech": scene.get("speech", ""),
        })

    result = {"scenes": filtered_scenes}

    stem = input_filename.removesuffix(".json")
    output_filename = f"{stem}_script_review.json"
    with open(output_filename, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Saved {len(filtered_scenes)} scenes to {output_filename}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python filter_json.py <input.json>")
        sys.exit(1)

    filter_scenes(sys.argv[1])