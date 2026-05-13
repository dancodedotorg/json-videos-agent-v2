# AG-UI CopilotKit Frontend — Progress & Remaining Work

Branch: `claude-plan-adk-only`

## What was built

### Phase 1 — Session state sync (complete)

**New file: `backend/tools/sync_video_state.py`**

Two ADK tools:
- `sync_to_state(unit, lesson, video, tool_context)` — reads `script.json` from disk, strips `scenes[n].html` (too large), writes result to `tool_context.state['script_json']`
- `apply_from_state(unit, lesson, video, tool_context)` — reads session state, merges only user-editable fields (`speech`, `comment`, `duration`) back to disk `script.json` via atomic write

**Updated: `backend/agent.py`**
- Imported and registered both functions as tools
- Added instructions: call `sync_to_state` after every pipeline skill; call `apply_from_state` before running video-script, video-html, video-audio-tags, video-audio, video-assemble

### Phase 2 — GCS artifact durability (skipped by design)

Decided: if Cloud Run recycles between pipeline stages, the user restarts from the last completed stage. No GCS save/restore needed.

### Phase 3 — CopilotKit frontend (complete, untested end-to-end)

**New directory: `frontend/`**

| File | Purpose |
|---|---|
| `package.json` | Next.js 15 + CopilotKit 1.56 + @ag-ui/client 0.0.52 |
| `next.config.ts` | Rewrites `/preview/*` and `/player/*` → ADK backend |
| `src/app/layout.tsx` | `<CopilotKit runtimeUrl="/api/copilotkit" agent="video_generation_agent">` |
| `src/app/page.tsx` | Split pane: chat (40%) + preview+editor (60%); `useCoAgent` binds to session state |
| `src/app/api/copilotkit/route.ts` | CopilotKit runtime proxy → `http://localhost:8080/agui` |
| `src/lib/types.ts` | `ScriptJson`, `Scene`, `Pipeline`, `AgentState` TypeScript types |
| `src/components/VideoPreview.tsx` | Loads `<json-video>` web component, polls `/preview/data/{unit}/{lesson}/{video}` every 3s |
| `src/components/SceneEditor.tsx` | Editable speech + comment per scene; read-only until script stage completes |
| `src/components/PipelineStatus.tsx` | Stage chips (grey/yellow/green) + link to standalone preview page |
| `src/global.d.ts` | TypeScript declaration for `<json-video>` web component |
| `README.md` | Dev setup instructions |

**Updated: `main.py`**
- Added `ag-ui-adk` AG-UI endpoint at `POST /agui` (wraps `root_agent` with `ADKAgent`, in-memory sessions)
- Added conditional `/app` static mount for production-built frontend

**Updated: `backend/requirements.txt`**
- Added `ag-ui-adk`

**Updated: `.gitignore`**
- Added `frontend/node_modules/`, `frontend/.next/`, `frontend/.env.local`

**Updated: all docs** (`README.md`, `ARCHITECTURE.md`, `frontend/README.md`)
- All `uvicorn` commands now include `--port 8080`

---

## How to run locally

```bash
# Terminal 1 — ADK backend + AG-UI endpoint + preview routes
source .venv/bin/activate
uvicorn main:app --reload --port 8080

# Terminal 2 — CopilotKit frontend (Node 20 required)
source ~/.nvm/nvm.sh && nvm use 20
cd frontend
cp .env.local.example .env.local   # first time only
npm install                        # first time only
npm run dev
```

Open **http://localhost:3000** for the CopilotKit frontend.
Open **http://localhost:8080** for the original ADK web UI (still works).

---

## What still needs to be done

### 1. End-to-end testing (highest priority)

The frontend built and the AG-UI endpoint registered, but the full state sync flow has not been tested:

- [ ] Chat in the CopilotKit frontend successfully starts an agent session
- [ ] Agent runs `video-init` → calls `sync_to_state` → `useCoAgent` state updates → `PipelineStatus` shows correct stages
- [ ] Agent runs `video-script` → `SceneEditor` populates with scenes
- [ ] User edits a speech field in `SceneEditor` → `setState` sends update back
- [ ] Agent runs `video-html` → calls `apply_from_state` first → edited speech appears in HTML
- [ ] `VideoPreview` shows the video once HTML slides exist
- [ ] Full pipeline runs to `video-assemble` → `VideoPreview` shows final assembled video

### 2. `/agui` endpoint uses in-memory sessions

`main.py` creates the AG-UI agent with `use_in_memory_services=True`. This means:
- Sessions are lost on server restart
- On Cloud Run, sessions are lost on instance recycle or scale-to-zero

**Fix for production**: Configure `ADKAgent` with the same Cloud SQL session service and GCS artifact service that `get_fast_api_app()` uses. Needs investigation — check `ag-ui-adk` docs for how to pass custom services.

### 3. Production deployment (Phase 4)

Next.js uses API routes (`/api/copilotkit`) which require a live Node.js server — `output: 'export'` (static files) is not compatible.

**Options:**
- **Two Cloud Run services**: ADK backend (existing) + Next.js frontend (new service). Set `AGENT_URL` env var on the frontend service to point to the ADK Cloud Run URL.
- **Single container with two processes**: Run uvicorn + Node in the same container via a process manager (adds complexity).

The simplest path is two Cloud Run services. The ADK backend already has an IAP-protected URL; the frontend service would need its own IAP configuration or could be public (CopilotKit auth would then handle access control).

### 4. `user_id` is hardcoded

`main.py` passes `user_id="copilot_user"` to `ADKAgent`. All sessions share the same user. For a multi-user deployment, this needs to be extracted from the request (e.g., from the IAP JWT or a CopilotKit auth header).

### 5. Minor UX polish (low priority)

- `VideoPreview` polls every 3s; consider connecting to the existing SSE stream at `/preview/stream/` instead for instant updates
- `SceneEditor` has no "unsaved changes" indicator to distinguish user edits from agent-generated content
- `PipelineStatus` doesn't show an in-progress spinner when the agent is actively running a stage
