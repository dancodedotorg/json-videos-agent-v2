"""
gemini-image-gen.py — Gemini image generation CLI tool

Generates a single image from a text prompt using Google's Gemini model and saves it to
tools/generated-images/. Designed to be called by an LLM during slide authoring.

USAGE
-----
    python tools/gemini-image-gen.py "<prompt>" [--aspect-ratio RATIO] [--reference-image PATH]

ARGUMENTS
---------
    prompt            Required. Text description of the image to generate.
    --aspect-ratio    Optional. One of: 1:1, 9:16, 16:9, 4:3, 3:4. Default: 16:9.
    --reference-image Optional. Path to a reference image. When provided, the image is passed
                      to Gemini alongside the prompt so it can replicate the character, setting,
                      and style. Use this for connected image sequences where visual continuity
                      across scenes matters.

OUTPUT
------
    stdout  Absolute filepath of the saved image — the only thing written to stdout.
            Consume this directly as the image src in a slide template.
    stderr  Logging/status messages (INFO level). Safe to ignore or redirect.

    Exit code 0 on success, 1 on failure.

EXAMPLES
--------
    python tools/gemini-image-gen.py "A dog barking at a mailbox, flat illustration style"
    python tools/gemini-image-gen.py "A busy server room filled with blinking lights" --aspect-ratio 16:9
    python tools/gemini-image-gen.py "The same dog now chasing a squirrel" --reference-image /path/to/scene_04.png

HOW AN LLM SHOULD USE THIS TOOL
---------------------------------
1.  Decide image generation is appropriate for the scene (see generation-guide.md).
2.  Follow the Video Director process in tools/video-director-prompt.md to assemble the prompt.
3.  Run this script with the assembled prompt and flags output by the Video Director.
4.  Capture the filepath printed to stdout.
5.  Insert it as the src attribute in the <img> tag of the slide template:
        <img src="/absolute/path/to/generated_image_<uuid>.png" alt="..." class="image">
6.  During final production, a separate pipeline converts local image paths to base64 data URIs.

PROMPT TIPS
-----------
- Choose subjects based on what the narration depicts — use literal subjects (a dog, a stage)
  when the scene names them; use abstract geometric forms for conceptual or data-driven scenes.
- Do NOT ask for text, labels, charts, or diagrams — use SVG for those instead.
- Avoid overly complex scenes with many interacting elements; simpler images render more reliably.

Good example:   "A friendly illustrated dog sitting alertly, ears perked, clean flat illustration style"
Weak example:   "AI doing things"

"""

from google import genai
from google.genai.types import GenerateContentConfig, ImageConfig
from PIL import Image
import argparse
import copy
import base64
import logging
import json
import sys
from typing import Any, Dict, List
from pydantic import BaseModel, Field
import uuid

# Load secrets
from dotenv import load_dotenv
import os
load_dotenv(os.path.join(os.getcwd(), "generation", "tools", ".env"))

logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                    format="%(levelname)s: %(message)s")

client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
logging.info("Gemini client initialized.")

GEMINI_IMG_MODEL = "gemini-3.1-flash-image-preview"

DEFAULT_OUTPUT_DIR = os.path.join(os.getcwd(), "generation", "tools", "generated-images")


def generate_image_for_scene(prompt: str, ratio: str = "16:9", reference_image_path: str = None, output_dir: str = None) -> str:
    """Generate an educational illustration for a tutorial video scene using Gemini.

    Args:
        prompt:               Description of the image to generate.
        ratio:                Aspect ratio — one of "1:1", "9:16", "16:9", "4:3", "3:4".
        reference_image_path: Optional path to a reference image for style/character continuity.
                              When provided, the image is passed alongside the prompt as multimodal input.
        output_dir:           Directory to save the image. Defaults to tools/generated-images/.

    Returns:
        Absolute path to the saved image file.

    Raises:
        RuntimeError: If Gemini returns no image data.
        Exception:    Re-raises any API error.
    """
    config = GenerateContentConfig(
        image_config=ImageConfig(
            aspect_ratio=ratio,
            image_size="1K"),
    )

    if reference_image_path:
        ref_image = Image.open(reference_image_path)
        contents = [prompt, ref_image]
        logging.info("Requesting image from Gemini (model=%s, ratio=%s, reference=%s)...", GEMINI_IMG_MODEL, ratio, reference_image_path)
    else:
        contents = prompt
        logging.info("Requesting image from Gemini (model=%s, ratio=%s)...", GEMINI_IMG_MODEL, ratio)

    response = client.models.generate_content(
        model=GEMINI_IMG_MODEL,
        contents=contents,
        config=config,
    )

    for part in response.parts:
        if part.inline_data is not None:
            image = part.as_image()

            save_dir = output_dir if output_dir else DEFAULT_OUTPUT_DIR
            os.makedirs(save_dir, exist_ok=True)
            filename = f"generated_image_{uuid.uuid4()}.png"
            filepath = os.path.join(save_dir, filename)

            image.save(filepath)

            logging.info("Image saved: %s", filepath)
            return filepath

    raise RuntimeError("Gemini returned no image data for the given prompt.")


def main():
    parser = argparse.ArgumentParser(
        description="Generate an image via Gemini and print the saved filepath to stdout."
    )
    parser.add_argument(
        "prompt",
        help="Text description of the image to generate.",
    )
    parser.add_argument(
        "--aspect-ratio",
        default="16:9",
        choices=["1:1", "9:16", "16:9", "4:3", "3:4"],
        dest="aspect_ratio",
        help="Aspect ratio of the generated image (default: 16:9).",
    )
    parser.add_argument(
        "--reference-image",
        default=None,
        dest="reference_image",
        help="Path to a reference image for style/character continuity (optional).",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        dest="output_dir",
        help="Directory to save the generated image. Defaults to tools/generated-images/.",
    )
    args = parser.parse_args()

    try:
        filepath = generate_image_for_scene(args.prompt, args.aspect_ratio, args.reference_image, args.output_dir)
        # Print only the filepath to stdout — clean for LLM consumption
        print(filepath)
    except Exception as e:
        logging.error("Image generation failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
