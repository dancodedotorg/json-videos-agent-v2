"""
preview_assemble.py — Build a player-ready preview JSON at any pipeline stage.

Like embed-data.py but designed to be called incrementally:
- Reads script.json as the base
- Loads scenes/scene_NN.html from disk if scenes[].html is empty
- Embeds local images and audio as base64 data URIs
- Returns the assembled dict (no zip archive side-effect)
- Missing files are silently skipped — partial states always render
"""

import base64
import hashlib
import json
import mimetypes
import re
import sys
from pathlib import Path


def path_to_data_uri(src: str, relative_to: Path = None) -> str | None:
    """Return a base64 data URI for a local file path, or None if not resolvable."""
    is_local = (
        src.startswith("file://")
        or re.match(r"^[A-Za-z]:[/\\]", src)
        or src.startswith("/")
    )
    if not is_local:
        return None

    path = Path(src.removeprefix("file:///").removeprefix("file://"))
    if not path.exists() and src.startswith("/"):
        alt = Path(".") / src.lstrip("/")
        if alt.exists():
            path = alt
    if not path.exists() and relative_to is not None:
        alt = relative_to / src.lstrip("/")
        if alt.exists():
            path = alt
    if not path.exists():
        return None

    mime, _ = mimetypes.guess_type(str(path))
    mime = mime or "application/octet-stream"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def _embed_local_images(html: str) -> str:
    """Replace local img src attributes in HTML with base64 data URIs."""
    def replace_src(match):
        quote = match.group(1)
        src = match.group(2)
        uri = path_to_data_uri(src)
        return f'src={quote}{uri}{quote}' if uri else match.group(0)

    return re.sub(r'src=(["\'])([^"\']+)\1', replace_src, html)


def get_state_hash(video_root: Path) -> str:
    """Hash of file mtimes in the video folder — changes when any relevant file is written."""
    h = hashlib.md5()
    script = video_root / "script.json"
    if script.exists():
        h.update(str(script.stat().st_mtime_ns).encode())
    for subdir in ("scenes", "audio"):
        d = video_root / subdir
        if d.exists():
            for f in sorted(d.iterdir()):
                if f.is_file():
                    h.update(f.name.encode())
                    h.update(str(f.stat().st_mtime_ns).encode())
    return h.hexdigest()


def build_preview_snapshot(video_root: Path) -> dict | None:
    """
    Assemble a player-ready dict from the current disk state of a video folder.
    Returns None if script.json doesn't exist yet.
    """
    script_path = video_root / "script.json"
    if not script_path.exists():
        return None

    try:
        data = json.loads(script_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    scenes_dir = video_root / "scenes"

    # Embed HTML + images for each scene
    for i, scene in enumerate(data.get("scenes", [])):
        html = scene.get("html", "")
        if not html:
            scene_file = scenes_dir / f"scene_{i + 1:02d}.html"
            if scene_file.exists():
                try:
                    html = scene_file.read_text(encoding="utf-8")
                except OSError:
                    continue
        if html:
            scene["html"] = _embed_local_images(html)

    # Embed audio
    tts_mode = data.get("tts", {}).get("mode", "")

    if tts_mode == "per_scene":
        for scene in data.get("scenes", []):
            audio_src = scene.get("audio", "")
            if not audio_src or audio_src.startswith("data:"):
                continue
            audio_path = (video_root / audio_src).resolve()
            uri = path_to_data_uri(str(audio_path))
            if uri:
                scene["audio"] = uri

    elif tts_mode == "combined":
        audio_src = data.get("audio", "")
        if audio_src and not audio_src.startswith("data:"):
            audio_path = (video_root / audio_src).resolve()
            uri = path_to_data_uri(str(audio_path))
            if uri:
                data["audio"] = uri

    return data
