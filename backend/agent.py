"""Video Generation Agent — runs the full video pipeline using ADK Skills.

Skills loaded (all from .agents/skills/):
  video-init, video-script, video-html, video-audio-tags,
  video-audio, video-assemble, video-create

Run from the project root:
  adk web backend/
"""

import pathlib

from dotenv import load_dotenv

PROJECT_ROOT = pathlib.Path(__file__).parent.parent

# Reuse the existing API keys — no duplicate .env needed
load_dotenv(PROJECT_ROOT / "generation" / "tools" / ".env", override=True)

from google.adk import Agent  # noqa: E402  (import after env setup)
from google.adk.environment import LocalEnvironment  # noqa: E402
from google.adk.skills import load_skill_from_dir  # noqa: E402
from google.adk.tools.environment import EnvironmentToolset  # noqa: E402
from google.adk.tools.load_artifacts_tool import LoadArtifactsTool  # noqa: E402
from google.adk.tools.skill_toolset import SkillToolset  # noqa: E402
from backend.tools.load_lesson_sources import load_lesson_sources  # noqa: E402
from backend.tools.ground_lesson import ground_lesson  # noqa: E402


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------

SKILLS_DIR = PROJECT_ROOT / ".agents" / "skills"

video_skills = [
    load_skill_from_dir(SKILLS_DIR / "video-init"),
    load_skill_from_dir(SKILLS_DIR / "video-script"),
    load_skill_from_dir(SKILLS_DIR / "video-html"),
    load_skill_from_dir(SKILLS_DIR / "video-audio-tags"),
    load_skill_from_dir(SKILLS_DIR / "video-audio"),
    load_skill_from_dir(SKILLS_DIR / "video-assemble"),
    load_skill_from_dir(SKILLS_DIR / "video-create"),
]

skill_toolset = SkillToolset(skills=video_skills)

# ---------------------------------------------------------------------------
# Environment — file I/O and script execution rooted at PROJECT_ROOT
# ---------------------------------------------------------------------------

env_toolset = EnvironmentToolset(
    environment=LocalEnvironment(working_dir=str(PROJECT_ROOT))
)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

root_agent = Agent(
    model="gemini-2.5-flash",
    name="video_generation_agent",
    description="Generates educational video content through a multi-stage pipeline of specialized skills.",
    instruction=(
        "You are a video generation agent for educational content. You use specialized skills "
        "to run a multi-stage pipeline:\n"
        "  video-init → video-script → video-html → video-audio-tags → video-audio → video-assemble\n\n"
        "When the user asks you to work on a video, extract the unit slug, lesson slug, and video "
        "name from their message. If any are missing, ask for them before loading a skill.\n\n"
        "Entry point for new lessons:\n"
        "When the user wants to make a video and provides a unit and lesson (number, name, or slug):\n"
        "1. Call ground_lesson(unit=<unit>, lesson=<lesson>) to check grounding status.\n"
        "   Handle each status:\n\n"
        "   'already_complete' → proceed to step 2.\n\n"
        "   'complete' or 'partial' → note any errors, proceed to step 2.\n\n"
        "   'sources_csv_generated' → sources.csv was generated from Code.org curriculum data.\n"
        "     It already contains the real lesson sources: Google Slides/Docs URLs, lesson level\n"
        "     ID, objectives, and vocabulary fetched from the API. Read it with read_file, then\n"
        "     show the user the full list: 'Here's what I found for this lesson — does this look\n"
        "     right? Let me know if you want to add, remove, or change any entries.' Wait for\n"
        "     confirmation and make any adjustments with write_file. Then call ground_lesson again\n"
        "     (it will proceed to grounding since sources.csv is confirmed on disk).\n\n"
        "   'needs_sources_csv' (standalone only) → there is no curriculum data to generate from.\n"
        "     Ask the user what materials to include: Google Slides URL, any objectives,\n"
        "     vocabulary, or Code.org lesson levels. Build sources.csv content from their answers,\n"
        "     show it for review: 'Here's the source list — does this look right?' Allow\n"
        "     conversational adjustments. Once confirmed, write it to\n"
        "     generation/units/standalone/lessons/<slug>/sources.csv, then call ground_lesson again.\n"
        "     The sources.csv format is CSV with columns: description, type, value.\n"
        "     Valid types: google_slides, google_doc, level_summary, objective, vocabulary.\n\n"
        "   'error' → report the error message and stop.\n\n"
        "2. Call load_lesson_sources(unit=<unit>, lesson=<lesson_slug>) using the lesson_slug\n"
        "   returned by ground_lesson.\n"
        "3. Load and run the video-init skill to set mode, objectives, and video name.\n"
        "4. Continue the full pipeline: video-script → video-html → video-audio-tags → "
        "video-audio → video-assemble.\n\n"
        "For standalone lessons (no Code.org unit): ask the user what slug they want to use for\n"
        "this lesson, then call ground_lesson('standalone', <slug>) to start the flow.\n\n"
        "Listing ready videos:\n"
        "When the user asks what's ready to generate or what videos are set up:\n"
        "- Use execute to list: generation/units/<unit>/lessons/<lesson>/videos/\n"
        "- For each video folder, use read_file to read its script.json and check the pipeline field.\n"
        "- Report each video's name and which pipeline stage it's at (pending/complete per stage).\n"
        "- If script.json is missing, the video needs to start from video-init.\n\n"
        "Tool usage:\n"
        "- ground_lesson — call with unit and lesson (number, slug, or name) to ensure source\n"
        "  materials are fetched. Two-phase: first call may return 'sources_csv_generated' for\n"
        "  user review; second call (after sources.csv is confirmed) runs the fetch.\n"
        "- load_skill_resource — load references/ files called out in skill instructions "
        "(e.g. references/concept-style-guide.md). Always use this for skill reference files, "
        "not read_file.\n"
        "- load_lesson_sources — call with unit and lesson slug to save lesson source materials "
        "(PDFs, JSON, markdown) as session artifacts. Idempotent. Call this before video-script "
        "runs on a lesson whose artifacts are not yet loaded.\n"
        "- load_artifacts — retrieve previously saved artifact content into the current turn's "
        "context as multimodal parts. Prefer this over read_file for PDFs and large JSON source "
        "files; artifact content is not persisted in session history.\n"
        "- read_file — read project files such as script.json; "
        "paths are relative to the project root\n"
        "- write_file — write project files; automatically creates any needed parent directories; "
        "paths are relative to the project root\n"
        "- execute — run shell commands in the project root, including listing directories "
        "(e.g. 'dir generation/units/unit/lessons') and running scripts "
        "(e.g. 'python .agents/skills/video-script/scripts/write-scenes.py arg1 arg2')\n\n"
        "Always load the relevant skill first to get detailed step-by-step instructions, "
        "then follow them precisely. Pause at every human check-in point and wait for "
        "the user's response before continuing."
    ),
    tools=[skill_toolset, env_toolset, LoadArtifactsTool(), load_lesson_sources, ground_lesson],
)
