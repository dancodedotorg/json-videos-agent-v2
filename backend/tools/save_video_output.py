"""Save the final video output files as downloadable session artifacts."""

import pathlib

import google.genai.types as types
from google.adk.tools.tool_context import ToolContext

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent


async def save_video_output(unit: str, lesson: str, video: str, tool_context: ToolContext) -> dict:
    """Save script.json and script_assembled_base64.json as downloadable session artifacts.

    Call this as the final step after video-assemble completes. Saves both files as
    artifacts so the user can download them from the ADK web UI. Neither file is
    loaded into the agent's context — artifacts are stored separately from conversation
    history and do not consume context window tokens.

    Args:
        unit: Unit slug (e.g. 'aif1-v2-2025')
        lesson: Lesson slug (e.g. 'lesson-2-beyond-words')
        video: Video name (e.g. 'objective-1')

    Returns:
        dict with keys:
            status    — 'saved', 'partial', or 'error'
            artifacts — mapping of filename to artifact name
            errors    — list of error messages
    """
    video_root = (
        PROJECT_ROOT / "generation" / "units" / unit / "lessons" / lesson / "videos" / video
    )
    saved: dict[str, str] = {}
    errors: list[str] = []

    for filename, mime_type in [
        ("script_assembled_base64.json", "application/json"),
        ("video_archive.zip", "application/zip"),
    ]:
        path = video_root / filename
        if not path.exists():
            errors.append(f"{filename} not found — run video-assemble first")
            continue
        artifact_name = f"{unit}__{lesson}__{video}__{filename}"
        part = types.Part.from_bytes(data=path.read_bytes(), mime_type=mime_type)
        await tool_context.save_artifact(filename=artifact_name, artifact=part)
        saved[filename] = artifact_name

    if not errors:
        status = "saved"
    elif saved:
        status = "partial"
    else:
        status = "error"

    return {"status": status, "artifacts": saved, "errors": errors}
