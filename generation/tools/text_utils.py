"""
text_utils.py -- Shared text sanitization utilities.
"""

from typing import Any


def normalize_text(text: str) -> str:
    """Replace Unicode typography with ASCII equivalents.

    LLMs commonly produce curly quotes, smart apostrophes, and fancy dashes.
    This ensures text passed to TTS APIs and written to output files stays clean.
    """
    return (
        text
        .replace("‘", "'")   # left single quotation mark
        .replace("’", "'")   # right single quotation mark / curly apostrophe
        .replace("“", '"')   # left double quotation mark
        .replace("”", '"')   # right double quotation mark
        .replace("–", "-")   # en dash
        .replace("—", " - ") # em dash
        .replace("…", "...") # ellipsis
    )


def normalize_data(obj: Any) -> Any:
    """Recursively apply normalize_text to all string values in a dict or list."""
    if isinstance(obj, str):
        return normalize_text(obj)
    if isinstance(obj, dict):
        return {k: normalize_data(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [normalize_data(item) for item in obj]
    return obj
