"""Load lesson source materials as ADK artifacts for the current session."""

import pathlib
import re

import google.genai.types as types
from google.adk.tools.tool_context import ToolContext

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent

_IMAGE_PATTERN = re.compile(r'(<img\s+src=\\?"data:image/png;(?:base64,)?)[^"\'<>\\\s]+')
_AUDIO_PATTERN = re.compile(r'("data:audio/mpeg;(?:base64,)?)[^"\'<>\\\s]+')


async def load_lesson_sources(unit: str, lesson: str, tool_context: ToolContext) -> dict:
    """Load lesson source materials (PDFs, JSON, markdown) as session artifacts.

    Reads files from the lesson's source/ folder and saves them as artifacts so
    they can be loaded into context via load_artifacts. Idempotent — if artifacts
    for this lesson already exist in the session, returns immediately without
    re-saving.

    Args:
        unit: Unit slug (e.g. 'aif1-v2-2025')
        lesson: Lesson slug (e.g. 'lesson-3-the-ais-brain')

    Returns:
        dict with keys: status ('loaded', 'already_loaded', 'partial', 'error'),
        artifacts (list of artifact names saved), errors (list of error messages).
    """
    source_dir = (
        PROJECT_ROOT / "generation" / "units" / unit / "lessons" / lesson / "source"
    )

    if not source_dir.exists():
        return {
            "status": "error",
            "artifacts": [],
            "errors": [
                f"Source directory not found: {source_dir}. "
                f"Run /lesson-ground {unit} {lesson} first."
            ],
        }

    # Idempotency: if any artifact with this lesson prefix already exists, skip
    prefix = f"{lesson}__"
    try:
        existing = await tool_context.list_artifacts()
        matching = [a for a in existing if a.startswith(prefix)]
        if matching:
            return {"status": "already_loaded", "artifacts": matching, "errors": []}
    except Exception:
        pass  # Proceed to save if listing fails

    saved: list[str] = []
    errors: list[str] = []

    for path in sorted(source_dir.iterdir()):
        name = path.name

        # Skip image files and leftover _cleaned.json artifacts from base64_clean.py
        if path.suffix in (".png", ".jpg", ".jpeg") or name.endswith("_cleaned.json"):
            continue

        # Normalize lesson_*_levels*.json to a stable artifact name
        if path.suffix == ".json" and path.stem.startswith("lesson_") and "levels" in path.stem:
            artifact_name = f"{prefix}lesson_levels.json"
        else:
            artifact_name = f"{prefix}{name}"

        try:
            if path.suffix == ".pdf":
                part = types.Part.from_bytes(
                    data=path.read_bytes(),
                    mime_type="application/pdf",
                )

            elif path.suffix == ".json":
                content = path.read_text(encoding="utf-8")
                # Strip base64 payloads (same patterns as base64_clean.py)
                content = _IMAGE_PATTERN.sub(r"\1", content)
                content = _AUDIO_PATTERN.sub(r"\1", content)
                part = types.Part.from_bytes(
                    data=content.encode("utf-8"),
                    mime_type="application/json",
                )

            elif path.suffix == ".md":
                part = types.Part.from_bytes(
                    data=path.read_bytes(),
                    mime_type="text/plain",
                )

            else:
                continue  # Skip unknown file types silently

            await tool_context.save_artifact(filename=artifact_name, artifact=part)
            saved.append(artifact_name)

        except Exception as e:
            errors.append(f"{name}: {e}")

    status = "loaded" if not errors else "partial"
    return {"status": status, "artifacts": saved, "errors": errors}
