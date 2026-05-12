# Cloud Run Deployment — Strategy Q&A

Fill in your answers below each question. Ping Claude when done.

---

## 1. Session Continuity

The filesystem being ephemeral is one thing — but the conversation itself is also ephemeral by default. The ADK `InMemorySessionService` means if the Cloud Run instance restarts mid-pipeline (between video-script and video-html, for example), the user's entire conversation context is gone too — not just the files. They'd have to restart the pipeline from scratch with no memory of what the agent already did.

**Is that acceptable? Or do you need conversation history to survive across turns even if generated files don't?** These are separable problems — you can have a persistent session backend (so the conversation survives restarts) while still accepting that files need to be regenerated.

**Answer:** It's also fine for conversations to be ephemeral. For this use case, the goal is to get to a place where the user has a script.json and script_assembled_base64.json file that they can save and use later.

---

## 2. Cloud Run Request Timeouts

Cloud Run kills HTTP requests after a configurable timeout — max 60 minutes, default 5 minutes. Your `execute` tool can invoke ElevenLabs audio generation or Google Slides fetching, which can be slow. A single `execute` call that runs `elevenlabs-gen.py` on a 15-scene video might take several minutes.

**Do you know roughly how long your slowest single tool call takes? And are you aware that if it exceeds the timeout, Cloud Run silently kills the request — causing the agent to hallucinate or error in confusing ways?**

**Answer:** None of these requests have taken more than 5 minutes; at most 3 minutes. I think we should try to configure this to timeout to at most 10 minutes.

---

## 3. Who Uses This

**Is this just you, or multiple developers?** And relatedly — do sessions need to be isolated between users? Right now the agent uses a single hardcoded `working_dir` pointing at `PROJECT_ROOT`. If two people run the agent simultaneously, they'd be writing to the same lesson folders on the same container instance (if they land on the same one), which causes collisions. If they land on different instances, they each get a fresh empty filesystem with no lesson data.

**Answer:** It's just internal users, and a very small subset of internal users likely running these one at a time. Their goal is to generate a video for a specific lesson as a json file. All of these potentials failure points are fine for now.

---

## 4. Interaction Model

There's a `NEXT_PUBLIC_BACKEND_URL=http://localhost:8000` in your `.env` files, which implies a frontend somewhere that talks to the ADK API server.

**What does the user actually open to use this agent?** The ADK dev UI (`--with_ui`), a custom frontend you've built or are building, or something else? This determines whether you deploy with `--with_ui`, whether you need CORS configured, and whether the Cloud Run URL becomes a backend URL or the primary user-facing URL.

**Answer:** This is a holdover from a previous iteration of this project that tried to build a different frontend with nextjs. We should delete this. I absolutely want to deploy with UI.

---

## 5. The `generation/units/` Data

If the filesystem is ephemeral, then `generation/units/aif1-v2-2025/` — with its `unit.json`, all grounded `source/` folders, all the `script.json` files — doesn't exist in the container at session start. The agent would have to re-ground every lesson from scratch every session.

**Is re-grounding on every session actually fine? Or were you imagining something like: the container image includes a snapshot of the current `generation/units/` directory baked in at build time?** The two strategies have very different implications — baked-in data means a new deploy per data update, but saves grounding time.

**Answer:** Ideally, I'd like to have the pre-grounded units exist when the image is created. I like the "snapshot of the generation/units directory" idea, and it's fine if updating that snapshot means a new deploy every time. But if that's not possible, it's fine to start empty and the user will need to ground every unit and lesson from scratch. 

---

## 6. Skills Outside `backend/`

The `adk deploy cloud_run backend/` command packages only the `backend/` directory. Your skills live at `.agents/skills/` and grounding scripts at `.agents/skills/lesson-ground/scripts/`. None of them would be in the container with that command.

**Are you planning to use a custom Dockerfile from the project root** — meaning you control exactly what goes in the image — or do you want to restructure so that everything the agent needs lives inside `backend/`?

**Answer:** Oh fascinating - I must've accidentally misaligned myself from the folder structure I need. I need those skill folders to be contained with the agent, so yes - I need to restructure so everything the agent needs lives inside backend. I guess that means some tools would get moved in there too?

---

## 7. Credential Handling

You have three secrets in play: `GOOGLE_API_KEY`, `ELEVENLABS_API_KEY`, and `GOOGLE_SERVICE_ACCOUNT_JSON` (the service account key for Google Slides/Docs access).

**How do you want to handle secrets on Cloud Run?** Options are: Secret Manager (most secure, requires setup), Cloud Run environment variables set at deploy time (simpler, visible in the console), or something else. And separately — **are the credentials currently in your `.env` files still the production ones you intend to use, or do they need to be rotated before going to Cloud Run?**

**Answer:** The current .env variables are the production ones. I want to use those.

---

## 8. Service Account Key vs. Attached Identity

The `GOOGLE_SERVICE_ACCOUNT_JSON` is specifically for authenticating to Google Slides and Docs APIs to fetch lesson materials during grounding. On Cloud Run, you could instead attach a service account to the Cloud Run service and use Application Default Credentials — no JSON key needed. The attached service account would need the same Slides/Docs read permissions.

**Do you want to eliminate the service account JSON key entirely** in favor of an attached service account identity, or keep the key-based approach and just move it to Secret Manager?

**Answer:** No I want to keep this JSON approach. 

---

## 9. Python Version

The `requirements-py313.txt` file suggests this was being developed with Python 3.12 in mind (standard `audioop` in pydub) but with a 3.13 path available.

**Do you have a preference on which Python version the container uses?**

**Answer:** I want to use 3.12

---

## 10. Concurrency

Cloud Run can run multiple concurrent requests per instance. Your pipeline does things like write `script.json`, then read it back, then write `scenes_draft.json`. If two requests were running concurrently on the same instance, they'd collide on those files.

**Should Cloud Run concurrency be set to 1** (one request at a time per instance, simpler but more expensive at scale) or higher? And does horizontal scaling (multiple instances) need to work, or is a single always-on instance the target?

**Answer:** I'm not sure about this one. I think setting concurrency to 1 makes sense, and I'm not planning on horizontal scaling. A single instance is fine, although it doesn't need to be "always on".

---

## 11. ADK Artifact Store

The `.adk/artifacts/` directory is where the local ADK server stores saved artifacts (the PDFs and JSON files you load with `save_artifact`). This is also ephemeral on Cloud Run — those artifacts are gone on restart. The `load_lesson_sources` tool would need to re-run every new session.

**Is the artifact re-loading per-session acceptable** the same way filesystem re-grounding is? Or do you want artifacts to survive across sessions (which requires a persistent artifact backend)?

**Answer:** Yes this is acceptable.
