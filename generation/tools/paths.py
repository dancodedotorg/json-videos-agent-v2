"""
paths.py — Canonical path helpers for the unit → lesson → video hierarchy.

All skills and tools derive folder/file paths through these functions.
Always call from the project root (json-video-player/).
"""

from pathlib import Path

GENERATION_ROOT = Path("generation")
UNITS_ROOT = GENERATION_ROOT / "units"


# ── Unit ──────────────────────────────────────────────────────────────────────

def unit_root(unit: str) -> Path:
    return UNITS_ROOT / unit

def unit_json(unit: str) -> Path:
    return unit_root(unit) / "unit.json"

def unit_lessons_json(unit: str) -> Path:
    return unit_root(unit) / "lessons.json"


# ── Lesson ────────────────────────────────────────────────────────────────────

def lesson_root(unit: str, lesson: str) -> Path:
    return unit_root(unit) / "lessons" / lesson

def lesson_sources_csv(unit: str, lesson: str) -> Path:
    return lesson_root(unit, lesson) / "sources.csv"

def lesson_state(unit: str, lesson: str) -> Path:
    return lesson_root(unit, lesson) / "lesson-state.json"

def lesson_source(unit: str, lesson: str) -> Path:
    return lesson_root(unit, lesson) / "source"

def lesson_videos_root(unit: str, lesson: str) -> Path:
    return lesson_root(unit, lesson) / "videos"


# ── Video ─────────────────────────────────────────────────────────────────────

def video_root(unit: str, lesson: str, video: str) -> Path:
    return lesson_videos_root(unit, lesson) / video

def video_script(unit: str, lesson: str, video: str) -> Path:
    return video_root(unit, lesson, video) / "script.json"

def video_audio_dir(unit: str, lesson: str, video: str) -> Path:
    return video_root(unit, lesson, video) / "audio"

def video_images_dir(unit: str, lesson: str, video: str) -> Path:
    return video_root(unit, lesson, video) / "images"

def video_scenes_dir(unit: str, lesson: str, video: str) -> Path:
    return video_root(unit, lesson, video) / "scenes"


# ── From script.json ─────────────────────────────────────────────────────────
# When you already have a loaded script dict, derive paths from its metadata.

def from_script(script: dict):
    """Return (unit, lesson, video) tuple from script.json metadata."""
    return script["unit"], script["lesson"], script["video_name"]
