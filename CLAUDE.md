# Claude Code Instructions

Read `AGENTS.md` for full project context, architecture, skill paths, tool descriptions, and generation workflow.

## Quick Reference

- Skills: `backend/skills/`
- Generation data: `generation/units/`
- Custom tools: `backend/tools/`
- Shared libs: `generation/tools/`
- Run locally: `adk web backend/`

## Skill script paths

Skill instructions reference scripts as `scripts/foo.py` relative to the skill directory. Always expand to the full project-relative path when running:

```
backend/skills/<skill-name>/scripts/<script>.py
```

Example: `python scripts/fetch_unit.py` in `unit-init` → `python backend/skills/unit-init/scripts/fetch_unit.py`

## Skill context

The 3 lesson/unit setup skills (`unit-init`, `lesson-init`, `lesson-ground`) are **Claude Code only** — they use Claude Code tools (Read, Write, Glob, Bash) and are not registered in the ADK web agent. The remaining 8 skills (`lesson-plan` + the 7 video pipeline skills) run in both Claude Code and ADK web.
