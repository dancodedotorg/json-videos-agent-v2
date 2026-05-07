"""Google Docs: export documents as PDF via the Drive export URL."""

import re
from typing import Any, Dict, Optional

import httpx


def extract_doc_id(url: str) -> Optional[str]:
    match = re.search(
        r'docs\.google\.com\/document(?:\/u\/\d+)?\/d\/([A-Za-z0-9_-]+)',
        url,
    )
    return match.group(1) if match else None


async def fetch_doc_as_pdf(export_url: str) -> Dict[str, Any]:
    headers = {"Accept": "application/pdf", "User-Agent": "google-fetch/1.0"}
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=httpx.Timeout(30.0)) as client:
            resp = await client.get(export_url, headers=headers)
        if resp.status_code >= 400:
            return {"status": "error", "message": f"HTTP {resp.status_code}"}
        content_type = (resp.headers.get("content-type") or "").lower()
        pdf_bytes = resp.content
        if "application/pdf" not in content_type and not pdf_bytes.startswith(b"%PDF"):
            return {"status": "error", "message": "Export did not return PDF. Doc may require authentication."}
        return {"status": "success", "pdf_bytes": pdf_bytes}
    except httpx.RequestError as e:
        return {"status": "error", "message": f"Network error: {e}"}
