# Plan: ADK Video Generation Agent

## Context

The project has 7 video generation skills in `.agents/skills/video-*/` following the agentskills.io spec, authored for Claude Code. The goal is a minimal Google ADK (Python) backend testable via `adk web` — no frontend, no AG-UI yet.

Two categories of work:
1. **Refactor SKILL.md files** to remove Claude Code-specific conventions
2. **Create `backend/agent.py`** — the ADK agent that loads skills + provides required tools

---

## Part 1: SKILL.md Refactoring (7 video skills)

### What changes and what stays — the key distinction

The agentskills.io spec uses **relative paths** for `references/` intentionally. `load_skill_resource` resolves them within the skill directory — these paths must stay relative and should not be made absolute. ✓ No path changes needed for references.

`scripts/` are different: they are **executed**, not loaded as resources. `load_skill_resource` does not run scripts. Our `run_python` tool receives the path, and it has no way to know which skill directory is "current" — so scripts must use project-relative paths that the tool can resolve from PROJECT_ROOT. `video-audio` and `video-assemble` already do this correctly (`.agents/skills/video-audio/scripts/...`). The other skills need to match.

---

### 1a. Frontmatter cleanup (all 7 skills)

Remove Claude Code-only fields — ADK ignores them:
- `allowed-tools` → remove
- `metadata.disable-model-invocation` → remove
- `metadata.argument-hint` → remove

Keep: `name`, `description`, `compatibility`.

### 1b. Replace `$ARGUMENTS` with conversational extraction (all 7 skills)

Current:
```
Parse `$ARGUMENTS` (3 words): UNIT=first, LESSON=second, VIDEO=third
```
Replace with: Extract unit slug, lesson slug, and video name from the user's message. If any are missing, ask for them before proceeding.

### 1c. Normalize executed script paths (video-script, video-html)

`video-audio` ✓ and `video-assemble` ✓ already use full project-relative paths. Update the remaining two to match:

**video-script** (2 changes):
- `python scripts/base64_clean.py` → `python .agents/skills/video-script/scripts/base64_clean.py`
- `python scripts/write-scenes.py` → `python .agents/skills/video-script/scripts/write-scenes.py`

**video-html** (4 changes):
- `python scripts/base64_clean.py` → `python .agents/skills/video-html/scripts/base64_clean.py`
- `python scripts/update-pipeline.py` → `python .agents/skills/video-html/scripts/update-pipeline.py`
- `python scripts/gemini-image-gen.py` → `python .agents/skills/video-html/scripts/gemini-image-gen.py`
- `python scripts/insert-slides.py` → `python .agents/skills/video-html/scripts/insert-slides.py`

### 1d. Replace "Read references/X" with explicit load_skill_resource calls (video-script, video-audio)

Paths stay relative per spec. Only the instruction verb changes:

`"Read references/concept-style-guide.md in full"`
→ `"Use load_skill_resource to read references/concept-style-guide.md in full"`

This matters because without it, the LLM may try `read_file("references/...")` which will fail.

### 1e. Replace slash-command "next step" instructions (video-script, video-html, video-audio, video-audio-tags)

Current: `"Run /video-html $UNIT $LESSON $VIDEO to generate HTML slides."`
Replace with: `"Tell the user to continue with the video-html skill for [unit] / [lesson] / [video]."`

### 1f. video-init: remove mkdir steps

`video-init` uses `Bash(mkdir *)` to create directories. Since `write_file` will auto-create parent dirs via `os.makedirs`, the explicit mkdir steps can be removed — just have it write the initial `script.json` directly.

---

## Part 2: backend/agent.py

Single file following the pattern in `documentation/example/app/agent.py`.

### Environment

```python
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / "generation" / "tools" / ".env", override=True)
```
Reuses existing keys — no new `.env` file needed.

### Model

`gemini-2.5-flash` (existing `GOOGLE_API_KEY`).

### Skills

```python
PROJECT_ROOT = pathlib.Path(__file__).parent.parent
SKILLS_DIR = PROJECT_ROOT / ".agents" / "skills"

skills = [
    load_skill_from_dir(SKILLS_DIR / "video-init"),
    load_skill_from_dir(SKILLS_DIR / "video-script"),
    load_skill_from_dir(SKILLS_DIR / "video-html"),
    load_skill_from_dir(SKILLS_DIR / "video-audio-tags"),
    load_skill_from_dir(SKILLS_DIR / "video-audio"),
    load_skill_from_dir(SKILLS_DIR / "video-assemble"),
    load_skill_from_dir(SKILLS_DIR / "video-create"),
]
```

### FunctionTools (4 tools replacing Claude Code built-ins)

All resolve paths relative to `PROJECT_ROOT`.

| Tool | Signature | Replaces |
|---|---|---|
| `read_file` | `(path: str) -> str` | Claude Code `Read` tool |
| `write_file` | `(path: str, content: str) -> str` | `Write`; auto-creates parent dirs |
| `list_directory` | `(path: str) -> str` | `Read` on directories |
| `run_python` | `(script_path: str, args: str = "") -> str` | `Bash(python *)`; cwd=PROJECT_ROOT; returns stdout+stderr |

### Agent instruction

Covers:
- Role and pipeline order: video-init → video-script → video-html → video-audio-tags → video-audio → video-assemble
- Extract unit/lesson/video from conversation; ask if missing
- Use `load_skill_resource` for `references/`, `read_file` for project files, `run_python` for scripts

### backend/requirements.txt

```
google-adk>=1.25.0
python-dotenv
```

---

## Critical files

- [.agents/skills/video-script/SKILL.md](.agents/skills/video-script/SKILL.md) — 1a, 1b, 1c, 1d, 1e
- [.agents/skills/video-html/SKILL.md](.agents/skills/video-html/SKILL.md) — 1a, 1b, 1c, 1e
- [.agents/skills/video-audio/SKILL.md](.agents/skills/video-audio/SKILL.md) — 1a, 1b, 1d, 1e
- [.agents/skills/video-audio-tags/SKILL.md](.agents/skills/video-audio-tags/SKILL.md) — 1a, 1b, 1e
- [.agents/skills/video-assemble/SKILL.md](.agents/skills/video-assemble/SKILL.md) — 1a, 1b
- [.agents/skills/video-init/SKILL.md](.agents/skills/video-init/SKILL.md) — 1a, 1b, 1f
- [.agents/skills/video-create/SKILL.md](.agents/skills/video-create/SKILL.md) — 1a, 1b
- [generation/tools/.env](generation/tools/.env) — source of API keys (not modified)
- [documentation/example/app/agent.py](documentation/example/app/agent.py) — structural template

---

## How to test

```bash
# From project root:
pip install -r backend/requirements.txt
adk web backend/
```

In the ADK web UI:
1. "What skills do you have?" — verifies all 7 L1 descriptions load
2. "Initialize a video called test-video for lesson 01 in unit aif1-v2-2025" — exercises video-init
3. "Generate a script for unit aif1-v2-2025, lesson 01, video test-video" — exercises video-script with mode selection
