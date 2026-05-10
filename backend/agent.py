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
from google.adk.tools.skill_toolset import SkillToolset  # noqa: E402


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
        "Tool usage:\n"
        "- load_skill_resource — load references/ files called out in skill instructions "
        "(e.g. references/concept-style-guide.md). Always use this for skill reference files, "
        "not read_file.\n"
        "- read_file — read project files such as script.json or source materials; "
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
    tools=[skill_toolset, env_toolset],
)
