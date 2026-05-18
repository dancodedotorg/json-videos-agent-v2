"""
embed-data.py — Embed all external assets into a script.json as base64 data URIs.

Converts every local file reference in a script to an inline data URI so the
video player can load assets without browser file-access restrictions:

  * Images:          <img> tags in scenes[].html whose src is a local file path
  * Per-scene audio: scenes[].audio paths  (when tts.mode == "per_scene")
  * Combined audio:  top-level "audio" path (when tts.mode == "combined")

Fake mode (tts.mode == "fake") skips audio embedding entirely.

USAGE
-----
    python tools/embed-data.py input.json [output.json]

    If output.json is omitted, the file is modified in-place.

EXIT CODES
----------
    0  Success
    1  Input file not found or unreadable
    2  JSON parse error
"""

import argparse
import base64
import json
import mimetypes
import re
import sys
import zipfile
from pathlib import Path


def path_to_data_uri(src: str, relative_to: Path = None) -> str | None:
    """Return a base64 data URI for a local file path, or None if not a local path."""
    # Treat as local if it looks like an absolute path (Windows or Unix) or file:// URI
    is_local = (
        src.startswith("file://")
        or re.match(r"^[A-Za-z]:[/\\]", src)  # Windows absolute: C:\... or C:/...
        or src.startswith("/")                  # Unix absolute
    )
    if not is_local:
        return None

    path = Path(src.removeprefix("file:///").removeprefix("file://"))
    if not path.exists() and src.startswith("/"):
        # On Windows, a Unix-style path like /generation/... resolves to the drive
        # root rather than the project root. Try CWD-relative as a fallback.
        alt = Path(".") / src.lstrip("/")
        if alt.exists():
            path = alt
    if not path.exists() and relative_to is not None:
        # Try resolving relative to the input file's directory
        alt = relative_to / src.lstrip("/")
        if alt.exists():
            path = alt
    if not path.exists():
        print(f"  WARNING: file not found, skipping: {path}", file=sys.stderr)
        return None

    mime, _ = mimetypes.guess_type(str(path))
    mime = mime or "application/octet-stream"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def create_source_archive(video_root: Path, archive_path: Path) -> int:
    """Zip script.json + scenes/ + images/ + audio/ for portable re-assembly. Returns file count."""
    EXCLUDE = {archive_path.name, "script_assembled_base64.json", "script_cleaned.json", "scenes_draft.json"}
    file_count = 0
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        script = video_root / "script.json"
        if script.exists():
            zf.write(script, "script.json")
            file_count += 1
        for subdir in ("scenes", "images", "audio"):
            d = video_root / subdir
            if d.exists():
                for f in sorted(d.iterdir()):
                    if f.is_file() and f.name not in EXCLUDE:
                        zf.write(f, f"{subdir}/{f.name}")
                        file_count += 1
    return file_count


def embed_local_images(html: str) -> tuple[str, int]:
    """Replace local img src attributes in HTML with data URIs. Returns (new_html, count)."""
    count = 0

    def replace_src(match):
        nonlocal count
        quote = match.group(1)
        src = match.group(2)
        uri = path_to_data_uri(src)
        if uri:
            count += 1
            return f'src={quote}{uri}{quote}'
        return match.group(0)

    result = re.sub(r'src=(["\'])([^"\']+)\1', replace_src, html)
    return result, count


def main():
    parser = argparse.ArgumentParser(
        description="Embed all external assets into a script.json as base64 data URIs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exit codes:
  0  Success
  1  Input file not found or unreadable
  2  JSON parse error

Examples:
  python embed-data.py script.json
  python embed-data.py script.json script_assembled_base64.json
""",
    )
    parser.add_argument("input", help="Path to input script.json")
    parser.add_argument("output", nargs="?", help="Output path (default: modify in-place)")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path

    if not input_path.exists():
        print(f"ERROR: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: JSON parse error: {e}", file=sys.stderr)
        sys.exit(2)

    # ── Embed images in scene HTML ──
    # HTML may live in scenes[].html (old behavior) or in scenes/scene_NN.html files
    # (deferred-insertion behavior). Try both, preferring the inline field.
    scenes_dir = input_path.parent / "scenes"
    image_total = 0
    for i, scene in enumerate(data.get("scenes", [])):
        html = scene.get("html", "")
        if not html:
            scene_file = scenes_dir / f"scene_{i + 1:02d}.html"
            if scene_file.exists():
                html = scene_file.read_text(encoding="utf-8")
                print(f"  Scene {i + 1}: loaded HTML from scenes/", file=sys.stderr)
            else:
                print(f"  WARNING: Scene {i + 1}: no html field and no {scene_file.name}", file=sys.stderr)
                continue
        new_html, count = embed_local_images(html)
        scene["html"] = new_html
        if count:
            image_total += count
            print(f"  Scene {i + 1}: embedded {count} image(s)", file=sys.stderr)

    # ── Embed audio ──
    tts_mode = data.get("tts", {}).get("mode", "")

    if tts_mode == "per_scene":
        audio_total = 0
        for i, scene in enumerate(data.get("scenes", [])):
            audio_src = scene.get("audio", "")
            if not audio_src or audio_src.startswith("data:"):
                continue
            # Resolve to absolute so path_to_data_uri's local-path check passes
            audio_path = (input_path.parent / audio_src).resolve()
            uri = path_to_data_uri(str(audio_path))
            if uri:
                scene["audio"] = uri
                audio_total += 1
                print(f"  Scene {i + 1} audio: embedded {Path(audio_src).name}", file=sys.stderr)
        if audio_total:
            print(f"  {audio_total} scene audio file(s) embedded", file=sys.stderr)

    elif tts_mode == "combined":
        audio_src = data.get("audio", "")
        if audio_src and not audio_src.startswith("data:"):
            audio_path = input_path.parent / audio_src
            uri = path_to_data_uri(str(audio_path))
            if uri:
                data["audio"] = uri
                print(f"  Audio: embedded {Path(audio_src).name}", file=sys.stderr)

    # tts_mode == "fake" or unset: skip audio silently

    if "pipeline" in data:
        data["pipeline"]["assembled"] = True

    output_path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
    print(f"Done. {image_total} image(s) embedded -> {output_path}", file=sys.stderr)

    archive_path = input_path.parent / "video_archive.zip"
    archive_count = create_source_archive(input_path.parent, archive_path)
    print(f"Archive: {archive_count} source file(s) -> {archive_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
