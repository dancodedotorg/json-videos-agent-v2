"""Google Slides API: fetch slide data, thumbnails, speaker notes, and render to PDF."""

import base64
import io
import re
from typing import Any, Dict, List, Optional

from xhtml2pdf import pisa

from lib.google_auth import (
    get_service_account_creds_from_env,
    _build_slides_service,
    _build_authed_session,
)


def extract_slides_id(url: str) -> Optional[str]:
    m = re.search(
        r'(?:docs\.google\.com\/presentation|drive\.google\.com\/file)?(?:\/u\/\d+)?\/d\/([A-Za-z0-9_-]+)',
        url,
    )
    return m.group(1) if m else None


def _get_slide_list(presentation_id: str, creds) -> List[Dict[str, Any]]:
    service = _build_slides_service(creds)
    presentation = service.presentations().get(presentationId=presentation_id).execute()
    return presentation.get("slides", [])


def get_all_speaker_notes_by_slide_id(
    presentation_id: str,
    creds,
    slides: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, str]:
    if slides is None:
        slides = _get_slide_list(presentation_id, creds)

    all_notes = {}
    for slide in slides:
        sid = slide["objectId"]
        notes_page = slide.get("slideProperties", {}).get("notesPage", {})
        note_texts = []
        for elem in notes_page.get("pageElements", []):
            shape = elem.get("shape")
            if not shape:
                continue
            if shape.get("placeholder", {}).get("type") != "BODY":
                continue
            for te in shape.get("text", {}).get("textElements", []):
                text_run = te.get("textRun")
                if text_run and "content" in text_run:
                    note_texts.append(text_run["content"])
        all_notes[sid] = "".join(note_texts).strip()

    return all_notes


def get_all_pngs_by_slide_id(
    presentation_id: str,
    creds,
    slides: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Optional[str]]:
    if slides is None:
        slides = _get_slide_list(presentation_id, creds)

    service = _build_slides_service(creds)
    authed_session = _build_authed_session(creds)
    png_images = {}

    for slide in slides:
        sid = slide["objectId"]
        thumbnail = (
            service.presentations()
            .pages()
            .getThumbnail(
                presentationId=presentation_id,
                pageObjectId=sid,
                thumbnailProperties_thumbnailSize="LARGE",
                thumbnailProperties_mimeType="PNG",
            )
            .execute()
        )
        image_content_url = thumbnail.get("contentUrl")
        if not image_content_url:
            png_images[sid] = None
            continue
        resp = authed_session.get(image_content_url, stream=True, timeout=30)
        resp.raise_for_status()
        b64 = base64.b64encode(resp.content).decode("utf-8")
        png_images[sid] = f"data:image/png;base64,{b64}"

    return png_images


def get_slides_data(presentation_id: str) -> List[Dict[str, Any]]:
    creds = get_service_account_creds_from_env()
    slides = _get_slide_list(presentation_id, creds)
    notes_by_id = get_all_speaker_notes_by_slide_id(presentation_id, creds, slides=slides)
    thumbs_by_id = get_all_pngs_by_slide_id(presentation_id, creds, slides=slides)

    slides_data = []
    for i, slide in enumerate(slides):
        sid = slide["objectId"]
        slides_data.append({
            "index": i,
            "slide_id": sid,
            "notes": notes_by_id.get(sid, ""),
            "png_base64": thumbs_by_id.get(sid, None),
        })
    return slides_data


def slides_to_pdf(slides: List[Dict[str, Any]]) -> str:
    """Render slides with speaker notes as a two-column PDF. Returns base64-encoded PDF string."""
    rows_html = ""
    for slide in slides:
        png = slide.get("png_base64") or ""
        notes = (slide.get("notes") or "").replace("\n", "<br/>")
        rows_html += f"""
        <tr>
          <td class="slide-col"><img src="{png}" /></td>
          <td class="notes-col">{notes}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <style>
    body {{ font-family: Arial, sans-serif; margin: 20px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border: 1px solid #ccc; padding: 8px; vertical-align: top; }}
    th {{ background-color: #f5f5f5; text-align: left; }}
    td.slide-col, th.slide-col {{ width: 200pt; }}
    td.notes-col, th.notes-col {{ width: 330pt; }}
    img {{ max-width: 100%; height: auto; display: block; }}
  </style>
</head>
<body>
  <table>
    <tr>
      <th class="slide-col">Slide</th>
      <th class="notes-col">Notes</th>
    </tr>
    {rows_html}
  </table>
</body>
</html>"""
    pdf_io = io.BytesIO()
    pisa.CreatePDF(io.StringIO(html), dest=pdf_io)
    return base64.b64encode(pdf_io.getvalue()).decode("utf-8")
