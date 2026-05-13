# Video Generation Frontend

CopilotKit + ADK frontend: split-pane chat + live video preview + scene editor.

## Prerequisites

- **Node.js 18+** (use `nvm use 20` on this machine)
- ADK backend running at `http://localhost:8080` via `uvicorn main:app --reload --port 8080` from the project root  
  (The frontend connects to the agent run endpoint at `http://localhost:8080/run`)

## Dev setup

```bash
# From project root — start the ADK backend
source .venv/bin/activate
uvicorn main:app --reload --port 8080

# In a second terminal — start the frontend
source ~/.nvm/nvm.sh && nvm use 20
cd frontend
cp .env.local.example .env.local   # only needed once
npm install
npm run dev
```

Open **http://localhost:3000**.

The frontend proxies `/preview/*` and `/player/*` to the ADK backend automatically, so both servers run in parallel without CORS issues.

## State flow

1. Agent runs a pipeline skill (video-init, video-script, etc.)
2. Agent calls `sync_to_state` → writes `script_json` to ADK session state
3. `useCoAgent` receives the state update → React components re-render
4. User edits a scene's speech text in SceneEditor
5. `setState` sends the edit back → session state updated
6. Next time the agent runs a skill, it calls `apply_from_state` first → picks up the edit

## Production

Next.js API routes (`/api/copilotkit`) require a Node.js server — static export is not supported. Deploy as a separate Cloud Run service pointing `AGENT_URL` at the ADK Cloud Run URL.
