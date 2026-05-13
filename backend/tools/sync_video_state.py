"""Sync script.json between disk and ADK session state for frontend live editing."""

import copy
import json
import pathlib

from google.adk.tools.tool_context import ToolContext

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent

_EDITABLE_SCENE_FIELDS = ("speech", "comment", "duration")


def _script_path(unit: str, lesson: str, video: str) -> pathlib.Path:
    return (
        PROJECT_ROOT
        / "generation" / "units" / unit / "lessons" / lesson / "videos" / video
        / "script.json"
    )


async def sync_to_state(
    unit: str, lesson: str, video: str, tool_context: ToolContext
) -> dict:
    """Read script.json from disk and write a stripped copy to session state.

    Strips scenes[n].html before writing — HTML is too large for session state.
    The frontend uses this state to display the scene editor and pipeline status.

    Call this after every pipeline skill completes (video-init, video-script,
    video-html, video-audio-tags, video-audio, video-assemble).

    Args:
        unit: Unit slug (e.g. 'aif1-v2-2025')
        lesson: Lesson slug (e.g. 'lesson-2-beyond-words')
        video: Video name (e.g. 'objective-1')

    Returns:
        dict with status, scene_count, pipeline
    """
    path = _script_path(unit, lesson, video)
    if not path.exists():
        return {"status": "error", "error": f"script.json not found at {path}"}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return {"status": "error", "error": f"JSON parse error: {e}"}

    state_data = copy.deepcopy(data)
    for scene in state_data.get("scenes", []):
        scene.pop("html", None)

    tool_context.state["script_json"] = state_data

    return {
        "status": "synced",
        "scene_count": len(state_data.get("scenes", [])),
        "pipeline": state_data.get("pipeline", {}),
    }


async def apply_from_state(
    unit: str, lesson: str, video: str, tool_context: ToolContext
) -> dict:
    """Apply user edits from session state back to disk script.json.

    Only writes user-editable scene fields: speech, comment, duration.
    Never touches html, audio paths, pipeline, or top-level metadata —
    those are agent-owned.

    Call this before video-script, video-html, video-audio-tags, video-audio,
    and video-assemble to pick up any edits the user made in the UI.

    Args:
        unit: Unit slug
        lesson: Lesson slug
        video: Video name

    Returns:
        dict with status and scenes_updated count
    """
    state_data = tool_context.state.get("script_json")
    if not state_data:
        return {"status": "no_state"}

    path = _script_path(unit, lesson, video)
    if not path.exists():
        return {"status": "error", "error": f"script.json not found at {path}"}

    try:
        disk_data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return {"status": "error", "error": f"JSON parse error: {e}"}

    state_scenes = state_data.get("scenes", [])
    disk_scenes = disk_data.get("scenes", [])
    updated = 0

    for i, state_scene in enumerate(state_scenes):
        if i >= len(disk_scenes):
            break
        for field in _EDITABLE_SCENE_FIELDS:
            if field in state_scene:
                disk_scenes[i][field] = state_scene[field]
        updated += 1

    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(disk_data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)

    return {"status": "applied", "scenes_updated": updated}
