"""CLI wrapper for ElevenLabs audio generation.

Reads scenes[].elevenlabs from a script.json, calls the ElevenLabs API,
saves the MP3 to audio/voiceover.mp3 (relative to script.json's folder),
and writes scenes[].duration back to script.json.

Usage:
    python elevenlabs-gen.py <path/to/script.json> [--voice Dan] [--fake]

Fake mode: skips the API call and assigns 3.0s to every scene.
"""

import argparse
import base64
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parents[4]
load_dotenv(_REPO_ROOT / "generation" / "tools" / ".env")

sys.path.insert(0, str(_REPO_ROOT / "generation" / "tools"))
from text_utils import normalize_text

AVAILABLE_VOICES = ["Dan", "Sam", "Adam", "Hope"]


def write_metadata(script: dict, provider: str, mode: str, voice: str | None = None, audio_file: str | None = None) -> dict:
    """Write tts.* and pipeline.audio into script so the LLM doesn't have to."""
    script.setdefault("tts", {})
    script["tts"]["provider"] = provider
    script["tts"]["mode"] = mode
    if voice:
        script["tts"]["voice"] = voice
    if audio_file:
        script["tts"]["file"] = audio_file
    else:
        script["tts"].pop("file", None)
    script.setdefault("pipeline", {})["audio"] = "complete"
    return script


def fake_generation(script: dict) -> dict:
    """Assign placeholder durations without calling ElevenLabs."""
    for scene in script.get("scenes", []):
        scene["duration"] = "3.00s"
    print(f"[fake] Assigned 3.0s duration to {len(script['scenes'])} scenes.")
    return script


def real_generation(script: dict, voice_name: str, output_dir: Path) -> dict:
    """Call ElevenLabs API, save MP3, and calculate per-scene durations."""
    # Import here so missing package only fails when actually needed
    try:
        from elevenlabs.client import ElevenLabs
    except ImportError:
        print("[error] elevenlabs package not installed. Run: pip install elevenlabs", file=sys.stderr)
        sys.exit(1)

    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("[error] ELEVENLABS_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)

    # Voice IDs
    voice_ids = {
        "Dan":  "0sqkv877qKv8jUXFfsXj",
        "Sam":  "w7LY6CndrQObaTsPvYeB",
        "Adam": "s3TPKV1kjDlVtZbl4Ksh",
        "Hope": "tnSpp4vdxKPjI9w0GnoV",
    }
    voice_id = voice_ids.get(voice_name)
    if not voice_id:
        print(f"[error] Unknown voice '{voice_name}'. Choose from: {AVAILABLE_VOICES}", file=sys.stderr)
        sys.exit(1)

    SCENE_SEPARATOR = " [pause] "
    MODEL = "eleven_v3"
    OUTPUT_FORMAT = "mp3_44100_128"

    scenes = script.get("scenes", [])
    texts = [normalize_text(s.get("elevenlabs", "")) for s in scenes]
    voiceover = SCENE_SEPARATOR.join(texts)

    print(f"[elevenlabs] Generating audio with voice '{voice_name}' ({len(voiceover)} chars)...")

    client = ElevenLabs(api_key=api_key)
    resp = client.text_to_speech.convert_with_timestamps(
        voice_id=voice_id,
        text=voiceover,
        model_id=MODEL,
        output_format=OUTPUT_FORMAT,
    )
    data = resp if isinstance(resp, dict) else getattr(resp, "dict", lambda: resp)()

    # Save MP3
    audio_b64 = data.get("audio_base64", "")
    if not audio_b64:
        print("[error] No audio_base64 in response", file=sys.stderr)
        sys.exit(1)

    audio_dir = output_dir / "audio"
    audio_dir.mkdir(exist_ok=True)
    mp3_path = audio_dir / "voiceover.mp3"
    mp3_path.write_bytes(base64.b64decode(audio_b64))
    print(f"[elevenlabs] MP3 saved to {mp3_path}")

    # Calculate durations
    alignment = data.get("alignment")
    if not alignment:
        print("[warn] No alignment data in response; setting all durations to 0s", file=sys.stderr)
        for scene in scenes:
            scene["duration"] = "0s"
        return script

    char_starts = alignment.get("character_start_times_seconds", [])
    char_ends = alignment.get("character_end_times_seconds", [])
    total_chars = len(char_starts)
    cursor = 0

    # EXPECT_CONTROL_ALIGNMENT_DATA = False for eleven_v3
    for i, scene in enumerate(scenes):
        text = scene.get("elevenlabs", "")
        text_len = len(text)

        if text_len == 0:
            scene["duration"] = "0s"
            continue

        start_idx = cursor
        end_idx = min(cursor + text_len - 1, total_chars - 1)

        if start_idx >= total_chars:
            print(f"[warn] Scene {i} out of alignment bounds; setting duration to 0s", file=sys.stderr)
            scene["duration"] = "0s"
            cursor += text_len
            continue

        try:
            t_start = char_starts[start_idx]
            t_end = char_ends[end_idx]
            duration = (t_end - t_start) + 0.5  # 0.5s breathing room
            scene["duration"] = f"{duration:.2f}s"
        except IndexError:
            scene["duration"] = "error"

        cursor += text_len
        # Separator: eleven_v3 converts [pause] to silence and omits from alignment
        # so we do NOT advance cursor for the separator text

    print(f"[elevenlabs] Durations calculated for {len(scenes)} scenes.")
    return script


def main():
    parser = argparse.ArgumentParser(description="Generate ElevenLabs audio for a video script.")
    parser.add_argument("script_path", help="Path to script.json")
    parser.add_argument("--voice", default="Dan", choices=AVAILABLE_VOICES, help="Voice name")
    parser.add_argument("--fake", action="store_true", help="Skip API call; assign placeholder durations")
    args = parser.parse_args()

    script_path = Path(args.script_path).resolve()
    if not script_path.exists():
        print(f"[error] File not found: {script_path}", file=sys.stderr)
        sys.exit(1)

    with open(script_path, encoding="utf-8") as f:
        script = json.load(f)

    output_dir = script_path.parent

    if args.fake:
        script = fake_generation(script)
        script = write_metadata(script, "fake", "fake")
        print("[mode] fake")
    else:
        script = real_generation(script, args.voice, output_dir)
        script = write_metadata(script, "elevenlabs", "combined", args.voice, "audio/voiceover.mp3")
        print("[mode] combined")

    tmp = script_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(script, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(script_path)

    print(f"[done] script.json updated at {script_path}")


if __name__ == "__main__":
    main()
