import asyncio
import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from backend.preview.preview_assemble import build_preview_snapshot, get_state_hash

router = APIRouter()

PROJECT_ROOT = Path(__file__).parent.parent.parent

_PREVIEW_PAGE = (Path(__file__).parent / "preview.html").read_text(encoding="utf-8")


def _video_root(unit: str, lesson: str, video: str) -> Path:
    return PROJECT_ROOT / "generation" / "units" / unit / "lessons" / lesson / "videos" / video


@router.get("/preview/{unit}/{lesson}/{video}", response_class=HTMLResponse)
async def preview_page(unit: str, lesson: str, video: str):
    stream_url = f"/preview/stream/{unit}/{lesson}/{video}"
    html = _PREVIEW_PAGE.replace("PREVIEW_STREAM_URL", f'"{stream_url}"')
    return HTMLResponse(content=html)


@router.get("/preview/stream/{unit}/{lesson}/{video}")
async def preview_stream(unit: str, lesson: str, video: str):
    video_root = _video_root(unit, lesson, video)

    async def event_generator():
        last_hash = None
        while True:
            try:
                current_hash = get_state_hash(video_root)
                if current_hash != last_hash:
                    last_hash = current_hash
                    snapshot = build_preview_snapshot(video_root)
                    if snapshot is None:
                        payload = {"type": "STATE_SNAPSHOT", "snapshot": {"_waiting": True}}
                    else:
                        payload = {"type": "STATE_SNAPSHOT", "snapshot": snapshot}
                    yield f"data: {json.dumps(payload)}\n\n"
                await asyncio.sleep(1.5)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(1.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/preview/data/{unit}/{lesson}/{video}")
async def preview_data(unit: str, lesson: str, video: str):
    video_root = _video_root(unit, lesson, video)
    snapshot = build_preview_snapshot(video_root)
    if snapshot is None:
        return JSONResponse(status_code=404, content={"error": "Video not found or pipeline not started"})
    return JSONResponse(content=snapshot)
