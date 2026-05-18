"""Code.org content fetching, PDF rendering, and text normalization."""

import base64
import io
import re
import sys
import urllib.parse
import urllib.request
from typing import Any, Optional

import httpx
from xhtml2pdf import pisa


async def fetch_markdown_level(name: str) -> Optional[str]:
    name_no_dashes = name.replace("-", "_").lower()
    url = (
        f"https://raw.githubusercontent.com/code-dot-org/code-dot-org"
        f"/refs/heads/staging/dashboard/config/scripts/{name_no_dashes}.external"
    )
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            response.raise_for_status()
        raw_text = response.text
        match = re.search(r"<<MARKDOWN\s*\n(.*?)\nMARKDOWN\s*$", raw_text, flags=re.DOTALL | re.MULTILINE)
        return match.group(1).strip() if match else None
    except Exception:
        return None


def encode_url(url: str) -> str:
    """Percent-encode a URL's path component, leaving the scheme/host/query intact."""
    parts = urllib.parse.urlsplit(url)
    encoded_path = urllib.parse.quote(parts.path, safe="/:@!$&'()*+,;=")
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, encoded_path, parts.query, parts.fragment))


def fetch_image_as_base64_url(url: str) -> Optional[str]:
    """Fetch an image URL and return as a base64 data URI. Returns None on any failure."""
    if not url:
        return None
    try:
        encoded = encode_url(url)
        with urllib.request.urlopen(encoded, timeout=10) as resp:
            content_type = resp.headers.get("Content-Type", "image/png").split(";")[0].strip()
            image_bytes = resp.read()
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        return f"data:{content_type};base64,{b64}"
    except Exception as e:
        print(f"[warn] Could not fetch image {encode_url(url)[:60]}: {e}", file=sys.stderr)
        return None


def panels_level_to_pdf(level_entry: dict) -> Optional[bytes]:
    """Render a Panels level as a PDF with image + text per panel.

    Returns PDF bytes, or None if panels list is empty or PDF generation fails.
    """
    panels = level_entry.get("panels", [])
    if not panels:
        return None

    rows_html = ""
    for panel in panels:
        text = (panel.get("text") or "").replace("\n", "<br/>")
        img_data_uri = fetch_image_as_base64_url(panel.get("imageUrl", ""))

        if img_data_uri:
            rows_html += f"""
        <tr>
          <td class="img-col"><img src="{img_data_uri}" /></td>
          <td class="text-col">{text}</td>
        </tr>"""
        else:
            rows_html += f"""
        <tr>
          <td colspan="2">{text}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <style>
    body {{ font-family: Arial, sans-serif; margin: 20px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    td {{ border: 1px solid #ccc; padding: 8px; vertical-align: top; }}
    td.img-col {{ width: 200pt; }}
    td.text-col {{ width: 330pt; }}
    img {{ max-width: 100%; height: auto; display: block; }}
  </style>
</head>
<body>
  <table>
    {rows_html}
  </table>
</body>
</html>"""

    pdf_io = io.BytesIO()
    result = pisa.CreatePDF(io.StringIO(html), dest=pdf_io)
    if result.err:
        print(f"[warn] PDF generation failed for panel level {level_entry.get('id')}", file=sys.stderr)
        return None
    return pdf_io.getvalue()


def inline_html_images(html: str) -> str:
    """Replace src URLs in all <img> tags with base64 data URIs.

    Handles both markdown-converted images and raw HTML <img> tags, catching
    URLs with spaces or other characters that xhtml2pdf can't fetch directly.
    Falls back to a percent-encoded URL if the fetch fails.
    """
    def replace_img(m):
        tag = m.group(0)

        def replace_src(sm):
            quote = sm.group(1)
            url = sm.group(2)
            if url.startswith("data:"):
                return sm.group(0)
            data_uri = fetch_image_as_base64_url(url)
            return f'src={quote}{data_uri}{quote}' if data_uri else f'src={quote}{encode_url(url)}{quote}'

        return re.sub(r'src=(["\'])([^"\']+)\1', replace_src, tag)

    return re.sub(r'<img[^>]+>', replace_img, html, flags=re.IGNORECASE)


def inline_markdown_images(markdown_text: str) -> str:
    """Replace markdown-style image URLs with base64 data URIs.

    Only handles ![alt](url) syntax. For HTML with raw <img> tags, use
    inline_html_images on the rendered HTML output instead.
    """
    def replace_image(m):
        alt = m.group(1)
        url = m.group(2)
        if url.startswith("data:"):
            return m.group(0)
        data_uri = fetch_image_as_base64_url(url)
        return f"![{alt}]({data_uri})" if data_uri else f"![{alt}]({encode_url(url)})"

    return re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', replace_image, markdown_text)


def external_level_to_pdf(level_entry: dict) -> Optional[bytes]:
    """Render an External level's markdown as a styled HTML PDF with images inlined.

    Returns PDF bytes, or None if markdown is empty or PDF generation fails.
    """
    try:
        import markdown as md_lib
    except ImportError:
        print("[warn] 'markdown' package not installed. Run: pip install markdown", file=sys.stderr)
        return None

    markdown_text = level_entry.get("markdown", "")
    if not markdown_text:
        return None

    # Convert markdown to HTML first, then inline all images at the HTML level.
    # This handles both markdown-style images and raw <img> tags embedded in the markdown.
    body_html = md_lib.markdown(markdown_text, extensions=["extra"])
    body_html = inline_html_images(body_html)

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <style>
    body {{ font-family: Arial, sans-serif; margin: 30px; line-height: 1.5; }}
    img {{ max-width: 100%; height: auto; display: block; margin: 10px 0; }}
    pre {{ background: #f5f5f5; padding: 10px; }}
    code {{ background: #f5f5f5; padding: 2px 4px; }}
    h1, h2, h3 {{ margin-top: 20px; }}
    table {{ border-collapse: collapse; width: 100%; }}
    td, th {{ border: 1px solid #ccc; padding: 6px 8px; }}
  </style>
</head>
<body>
{body_html}
</body>
</html>"""

    pdf_io = io.BytesIO()
    result = pisa.CreatePDF(io.StringIO(html), dest=pdf_io)
    if result.err:
        print(f"[warn] PDF generation failed for external level {level_entry.get('id')}", file=sys.stderr)
        return None
    return pdf_io.getvalue()


def clean_codeorg_markdown(text: str) -> str:
    """Normalize Code.org markdown for LLM readability.

    - Normalizes CRLF to LF
    - Flattens ::: details blocks to **Title**\ncontent (strips HTML icon tags from titles)
    - Removes stray &nbsp entities
    - Collapses excessive blank lines
    """
    if not text:
        return text

    text = text.replace("\r\n", "\n").replace("\r", "\n")

    def flatten_details(m):
        raw_title = m.group(1)
        content = m.group(2).strip()
        clean_title = re.sub(r"<[^>]+>", "", raw_title).strip().strip("*").strip()
        return f"**{clean_title}**\n{content}"

    text = re.sub(
        r":::[ ]?details \[([^\]]*)\]\s*\n(.*?)\n:::",
        flatten_details,
        text,
        flags=re.DOTALL,
    )

    text = text.replace("&nbsp;", "").replace("&nbsp", "")
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_text_fields(obj: Any) -> Any:
    """Recursively apply clean_codeorg_markdown to all string values."""
    if isinstance(obj, dict):
        return {k: clean_text_fields(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_text_fields(item) for item in obj]
    if isinstance(obj, str):
        return clean_codeorg_markdown(obj)
    return obj
