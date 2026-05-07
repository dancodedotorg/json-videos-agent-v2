"""CLI wrapper for fetching content from Google sources and Code.org.

Reads source material from Google Slides, Google Docs, Code.org GitHub,
or Code.org lesson level data and saves it to an output directory.

Usage:
    python google-fetch.py google_slides <url> <output-dir>
    python google-fetch.py google_doc <url> <output-dir>
    python google-fetch.py codeorg_markdown <level-name> <output-dir>
    python google-fetch.py level_summary <lesson-id> <output-dir>

Outputs:
    google_slides  → output-dir/slide_01.png, slide_02.png, ..., slides_data.json, slides_notes.pdf
    google_doc     → output-dir/<doc-id>.pdf
    codeorg_markdown → output-dir/<level-name>.md
    level_summary  → output-dir/lesson_<id>_levels.json, panels_level_<id>.pdf (per Panels level),
                     external_level_<id>.pdf (per External level)
"""

import argparse
import asyncio
import base64
import json
import sys
import urllib.request
from pathlib import Path

from lib.google_slides import get_slides_data, slides_to_pdf, extract_slides_id
from lib.google_docs import fetch_doc_as_pdf, extract_doc_id
from lib.codeorg import (
    fetch_markdown_level,
    panels_level_to_pdf,
    external_level_to_pdf,
    clean_text_fields,
)

# Resolve repo root from __file__ location (cwd-independent)
# google-fetch.py -> scripts -> lesson-ground -> skills -> .agents -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_REPO_ROOT / "generation" / "tools"))
from text_utils import normalize_text, normalize_data


# --------------------------------
# CLI handlers
# --------------------------------

def fetch_google_slides(url: str, output_dir: Path) -> dict:
    """Download slide thumbnails as PNGs, slides_data.json, and slides_notes.pdf."""
    presentation_id = extract_slides_id(url)
    if not presentation_id:
        presentation_id = url.strip()

    if not presentation_id:
        print("[error] Could not extract presentation ID from URL.", file=sys.stderr)
        sys.exit(1)

    print(f"[slides] Fetching slides for presentation: {presentation_id}")
    slides_data = get_slides_data(presentation_id)

    if not slides_data:
        print("[error] No slides data returned. Check GOOGLE_SERVICE_ACCOUNT_JSON.", file=sys.stderr)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate combined slides+notes PDF before base64 is stripped from each slide
    pdf_b64 = slides_to_pdf(slides_data)
    pdf_path = output_dir / "slides_notes.pdf"
    pdf_path.write_bytes(base64.b64decode(pdf_b64))
    print(f"[slides] Saved slides_notes.pdf")

    png_count = 0
    for slide in slides_data:
        idx = slide["index"] + 1
        png_b64 = slide.get("png_base64")

        if png_b64:
            if png_b64.startswith("data:image/png;base64,"):
                png_b64 = png_b64[len("data:image/png;base64,"):]
            png_path = output_dir / f"slide_{idx:02d}.png"
            png_path.write_bytes(base64.b64decode(png_b64))
            slide["png_base64"] = None
            png_count += 1
            print(f"[slides] Saved {png_path.name}")

    data_path = output_dir / "slides_data.json"
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(slides_data, f, indent=2, ensure_ascii=False)

    print(f"[slides] Saved {png_count} slide PNGs, slides_data.json, and slides_notes.pdf to {output_dir}")
    return {"slide_count": png_count, "data_file": str(data_path), "pdf_file": str(pdf_path)}


def fetch_google_doc(url: str, output_dir: Path) -> dict:
    """Export a Google Doc as PDF and save to output_dir."""
    doc_id = extract_doc_id(url)
    if not doc_id:
        doc_id = url.strip()

    if not doc_id:
        print("[error] Could not extract document ID from URL.", file=sys.stderr)
        sys.exit(1)

    export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=pdf"
    print(f"[doc] Fetching Google Doc: {doc_id}")

    result = asyncio.run(fetch_doc_as_pdf(export_url))

    if result.get("status") == "error":
        print(f"[error] {result.get('message', 'Unknown error')}", file=sys.stderr)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / f"{doc_id}.pdf"
    pdf_path.write_bytes(result["pdf_bytes"])
    print(f"[doc] Saved {pdf_path}")
    return {"pdf_file": str(pdf_path)}


def fetch_codeorg_markdown(level_name: str, output_dir: Path) -> dict:
    """Fetch a Code.org curriculum markdown level from GitHub."""
    print(f"[markdown] Fetching Code.org level: {level_name}")

    content = asyncio.run(fetch_markdown_level(level_name))

    if not content:
        print(f"[error] Could not fetch markdown for level '{level_name}'.", file=sys.stderr)
        print("Check the level name format (e.g., 'Unit3-Lesson5' or 'CSD-U3-L5').", file=sys.stderr)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / f"{level_name}.md"
    md_path.write_text(normalize_text(content), encoding="utf-8")
    print(f"[markdown] Saved {md_path}")
    return {"markdown_file": str(md_path)}


def fetch_level_summary(lesson_id: str, output_dir: Path) -> dict:
    """Fetch and filter level data for a Code.org lesson, then generate panel and external PDFs."""
    filter_path = Path(__file__).parent / "level_types_filter.json"
    with open(filter_path, encoding="utf-8") as f:
        to_keep = json.load(f)

    url = f"https://studio.code.org/lessons/{lesson_id}/level_properties"
    print(f"[levels] Fetching {url} ...")

    try:
        with urllib.request.urlopen(url) as response:
            levels_data = json.loads(response.read().decode())
    except Exception as e:
        print(f"[error] Could not fetch lesson {lesson_id}: {e}", file=sys.stderr)
        sys.exit(1)

    def filter_by_spec(data, spec):
        result = {}
        for key, spec_value in spec.items():
            if key not in data:
                continue
            value = data[key]
            if isinstance(spec_value, dict):
                if isinstance(value, list):
                    result[key] = [filter_by_spec(item, spec_value) for item in value if isinstance(item, dict)]
                elif isinstance(value, dict):
                    result[key] = filter_by_spec(value, spec_value)
            else:
                result[key] = value
        return result

    filtered = {}
    for level_id, level_data in levels_data.items():
        level_type = level_data.get("type")
        if level_type not in to_keep:
            continue
        entry = {"id": level_data.get("id"), "type": level_type}
        entry.update(filter_by_spec(level_data, to_keep[level_type]))
        filtered[level_id] = clean_text_fields(entry)

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"lesson_{lesson_id}_levels.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(normalize_data(filtered), f, indent=2, ensure_ascii=False)

    print(f"[levels] Lesson {lesson_id}: {len(levels_data)} levels → {len(filtered)} kept → {out_path.name}")

    # Generate a PDF for each Panels-type level
    panel_pdf_count = 0
    for entry in filtered.values():
        if entry.get("type") != "Panels":
            continue
        pdf_bytes = panels_level_to_pdf(entry)
        if pdf_bytes:
            pdf_path = output_dir / f"panels_level_{entry['id']}.pdf"
            pdf_path.write_bytes(pdf_bytes)
            print(f"[levels] Saved {pdf_path.name}")
            panel_pdf_count += 1

    if panel_pdf_count:
        print(f"[levels] Generated {panel_pdf_count} panel PDF(s)")

    # Generate a PDF for each External-type level
    external_pdf_count = 0
    for entry in filtered.values():
        if entry.get("type") != "External":
            continue
        pdf_bytes = external_level_to_pdf(entry)
        if pdf_bytes:
            pdf_path = output_dir / f"external_level_{entry['id']}.pdf"
            pdf_path.write_bytes(pdf_bytes)
            print(f"[levels] Saved {pdf_path.name}")
            external_pdf_count += 1

    if external_pdf_count:
        print(f"[levels] Generated {external_pdf_count} external PDF(s)")

    return {
        "levels_file": str(out_path),
        "total": len(levels_data),
        "kept": len(filtered),
        "panel_pdfs": panel_pdf_count,
        "external_pdfs": external_pdf_count,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "type",
        choices=["google_slides", "google_doc", "codeorg_markdown", "level_summary"],
        help="Source type",
    )
    parser.add_argument(
        "url_or_name",
        help="URL for Google sources, level name for Code.org markdown, or lesson ID for level_summary",
    )
    parser.add_argument("output_dir", help="Directory to save output files")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()

    if args.type == "google_slides":
        result = fetch_google_slides(args.url_or_name, output_dir)
    elif args.type == "google_doc":
        result = fetch_google_doc(args.url_or_name, output_dir)
    elif args.type == "codeorg_markdown":
        result = fetch_codeorg_markdown(args.url_or_name, output_dir)
    elif args.type == "level_summary":
        result = fetch_level_summary(args.url_or_name, output_dir)

    print(f"[done] {json.dumps(result)}")


if __name__ == "__main__":
    main()
