"""CLI wrapper for Gemini TTS audio generation.

Reads scenes[].gemini from a script.json, calls the Gemini TTS API,
saves per-scene MP3s to audio/scene_NN.mp3 (relative to script.json's folder),
and writes scenes[].duration and scenes[].audio back to script.json.

Usage:
    python gemini-audio-gen.py <path/to/script.json> [--voice Zephyr] [--fake]

Fake mode: assigns 3.0s to every scene, no API calls.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Force line-buffered stdout so progress prints appear immediately
sys.stdout.reconfigure(line_buffering=True)

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parents[4]
load_dotenv(_REPO_ROOT / "generation" / "tools" / ".env")

sys.path.insert(0, str(_REPO_ROOT / "generation" / "tools"))
from text_utils import normalize_text

AVAILABLE_VOICES = ["Zephyr", "Puck", "Aoede", "Kore", "Fenrir"]
DEFAULT_VOICE = "Zephyr"
MODEL = "gemini-3.1-flash-tts-preview"
MAX_RETRIES = 3

PERSONA_TEMPLATE = """\
# AUDIO PROFILE: Educational Narrator
## "The Clear Explainer"

### DIRECTOR'S NOTES
Style: Clear, warm, and engaging educator. Patient and encouraging without being condescending.
Pace: Moderate, with natural variation — slower for key concepts, slightly faster for transitions.

### TRANSCRIPT
{gemini_text}\
"""

DETAILED_PERSONA_TEMPLATE = """\
# AUDIO PROFILE: Jordan M.
## "The Explainer"

## THE SCENE: The Recording Studio
A quiet, warmly lit recording booth. No background noise — just the faint hum of
studio monitors. Jordan is seated comfortably at a microphone, script printed and
annotated in hand. There's no audience watching — just Jordan and the listener.
The mood is calm, focused, and unhurried. This is a recorded lesson, not a live
performance. Jordan knows the material well and genuinely wants the listener to
understand it.

### DIRECTOR'S NOTES

Style: Clear, grounded educator. Jordan teaches with confidence but never talks
down to students. The delivery has warmth without being cheerful or performative.
When explaining a new idea, slow down slightly and let the concept land before
moving on. Treat the listener as smart and capable.

Pacing: Moderate — unhurried but never dragging. Slight natural pauses after key
terms or before a new idea. No rushed sentences. Think "thoughtful podcast host"
rather than "excited presenter." Slower for key concepts, slightly faster for transitions.

Accent: Neutral American English. No regional features. Clear consonants and
fully enunciated vowel sounds for easy comprehension.

### SAMPLE CONTEXT
Jordan is recording voice narration for a video lesson about AI used in a middle
or high school classroom. Students are watching this on their own or in class.
The goal is understanding, not entertainment. Every sentence should feel like it
was worth saying.

#### TRANSCRIPT
{gemini_text}\
"""



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


def fake_generation(script: dict, output_dir: Path) -> dict:
    """Assign 3.0s durations to all scenes without calling the API."""
    scenes = script.get("scenes", [])
    print(f"[fake] {len(scenes)} scenes — assigning 3.0s each")
    for i, scene in enumerate(scenes):
        scene["duration"] = "3.00s"
        print(f"[fake] scene {i+1}/{len(scenes)} done")
    return script


def real_generation(script: dict, voice_name: str, output_dir: Path) -> dict:
    """Call Gemini TTS API per scene, save MP3s, and calculate durations."""
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("[error] google-genai package not installed. Run: pip install google-genai", file=sys.stderr)
        sys.exit(1)

    try:
        from pydub import AudioSegment
    except ImportError:
        print("[error] pydub package not installed. Run: pip install pydub", file=sys.stderr)
        sys.exit(1)

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[error] GOOGLE_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    audio_dir = output_dir / "audio"
    audio_dir.mkdir(exist_ok=True)

    scenes = script.get("scenes", [])
    total = len(scenes)
    run_start = time.time()

    print(f"[gemini] Starting — {total} scenes, voice '{voice_name}', model {MODEL}")

    for i, scene in enumerate(scenes):
        gemini_text = normalize_text(scene.get("gemini", ""))
        if not gemini_text:
            print(f"[warn] scene {i+1}/{total} has no 'gemini' field; skipping")
            scene["duration"] = "0s"
            continue

        # prompt = DETAILED_PERSONA_TEMPLATE.format(gemini_text=gemini_text)
        prompt = PERSONA_TEMPLATE.format(gemini_text=gemini_text)
        mp3_path = audio_dir / f"scene_{i+1:02d}.mp3"
        label = f"scene {i+1}/{total}"

        pcm_data = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                print(f"[gemini] {label} — calling API (attempt {attempt})...")
                t0 = time.time()
                response = client.models.generate_content(
                    model=MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name=voice_name
                                )
                            )
                        ),
                    ),
                )
                api_elapsed = time.time() - t0
                part = response.candidates[0].content.parts[0]
                inline = part.inline_data
                if inline is None or not inline.data:
                    raise ValueError("Response contained no audio data (possible text token return)")
                pcm_data = inline.data
                print(f"[gemini] {label} — API responded in {api_elapsed:.1f}s")
                break
            except Exception as exc:
                print(f"[warn] {label} attempt {attempt} failed: {exc}")
                if attempt < MAX_RETRIES:
                    wait = 2 ** attempt
                    print(f"[gemini] {label} — retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"[error] {label} failed after {MAX_RETRIES} attempts; setting duration to 0s")
                    scene["duration"] = "0s"

        if pcm_data is None:
            continue

        print(f"[gemini] {label} — saving {mp3_path.name}...")
        # PCM from Gemini: 16-bit, 24 kHz, mono
        audio = AudioSegment(data=pcm_data, sample_width=2, frame_rate=24000, channels=1)
        audio.export(mp3_path, format="mp3")

        duration_s = len(audio) / 1000.0
        file_kb = mp3_path.stat().st_size // 1024
        scene["duration"] = f"{duration_s + 0.5:.2f}s"
        scene["audio"] = f"audio/scene_{i+1:02d}.mp3"
        elapsed_total = time.time() - run_start
        print(f"[gemini] {label} — done  {duration_s:.2f}s audio + 0.5s pad = {duration_s + 0.5:.2f}s  |  {file_kb}KB  |  {i+1}/{total} complete  |  {elapsed_total:.0f}s elapsed")

    total_elapsed = time.time() - run_start
    print(f"[gemini] All {total} scenes processed in {total_elapsed:.0f}s")
    return script


def main():
    parser = argparse.ArgumentParser(description="Generate Gemini TTS audio for a video script.")
    parser.add_argument("script_path", help="Path to script.json")
    parser.add_argument("--voice", default=DEFAULT_VOICE, choices=AVAILABLE_VOICES, help="Voice name")
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
        script = fake_generation(script, output_dir)
        script = write_metadata(script, "fake", "fake")
        print("[mode] fake")
    else:
        script = real_generation(script, args.voice, output_dir)
        script = write_metadata(script, "gemini", "per_scene", args.voice)
        print("[mode] per_scene")

    tmp = script_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(script, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(script_path)

    print(f"[done] script.json written → {script_path}")


if __name__ == "__main__":
    main()
