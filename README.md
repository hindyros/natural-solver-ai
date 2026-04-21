# Op-Σra — AI Optimization Consulting

Natural-language optimization problem → consultant-grade report, powered by a multi-agent StackAI pipeline.

---

## Tech Stack

| Layer | Service | Purpose |
|---|---|---|
| **Frontend** | [Vercel](https://vercel.com) | Hosts the React/Vite app |
| **Frontend framework** | React 18 + TypeScript + Vite | UI |
| **Styling** | Tailwind CSS + shadcn/ui | Component library & design system |
| **Markdown rendering** | react-markdown + remark-gfm | Renders the consultant report |
| **Diagrams** | Mermaid.js | Renders optimization diagrams (pie, flowchart) |
| **Backend** | [Render](https://render.com) (free tier) | Express/Node.js API server |
| **Job store** | [Upstash Redis](https://upstash.com) | Persists async job state across server restarts |
| **AI pipeline** | [StackAI](https://stack-ai.com) | Multi-agent flow: formulator → auditor → code gen → validator |

---

## Architecture

```
Browser
  │
  ├─ POST /api/stack-run  ──▸  Express (Render)  ──▸  StackAI pipeline
  │       returns { jobId }         │                    (Opus 4.6 + Sonnet 4.6)
  │                                 │
  │                           Upstash Redis
  │                           job:{ status, output }
  │
  └─ GET /api/status/:jobId  ──▸  Express  ──▸  Redis GET
         polls every 3s              returns { status: "running" | "done" | "error" }
```

**Key design decisions:**
- The initial POST returns a `jobId` immediately (<1s) — no long-lived HTTP connection
- The StackAI call runs as a background job; the frontend polls for completion
- Redis persists job state so results survive Render restarts and browser tab throttling
- Jobs expire automatically after 1 hour (Redis TTL)
- Fetch timeouts: 60s per file upload, 270s for the AI flow run

API keys live **only on the backend**. The frontend never sees them.

---

## Environment Variables

### Backend (Render)

| Variable | Description |
|---|---|
| `STACK_AI_PUBLIC_KEY` | StackAI API key |
| `STACK_AI_ORG_ID` | StackAI organisation ID |
| `STACK_AI_FLOW_ID` | StackAI flow ID |
| `UPSTASH_REDIS_REST_URL` | Upstash Redis REST endpoint |
| `UPSTASH_REDIS_REST_TOKEN` | Upstash Redis auth token |

### Frontend (Vercel)

| Variable | Description |
|---|---|
| `VITE_API_URL` | Backend URL, e.g. `https://natural-solver-ai.onrender.com` |

---

## Deploy

### Backend (Render)

1. [render.com/new](https://render.com/new) → **Blueprint** → connect this repo
2. Render reads `render.yaml` and creates the service
3. Add the five env vars above under Environment
4. Deploy — note the service URL

### Redis (Upstash)

1. [upstash.com](https://upstash.com) → create a free Redis database
2. Copy `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` into Render env vars

### Frontend (Vercel)

1. [vercel.com/new](https://vercel.com/new) → import this repo
2. Add env var: `VITE_API_URL` = your Render backend URL (no trailing slash)
3. Deploy

---

## Agent API

Op-Era exposes a REST API that AI agents can use directly — no browser required.

**Protocol files** (start here):

| URL | Purpose |
|---|---|
| [`https://natural-solver-ai.onrender.com/skill.md`](https://natural-solver-ai.onrender.com/skill.md) | Full skill manifest — registration, submission, polling, tips |
| [`https://natural-solver-ai.onrender.com/heartbeat.md`](https://natural-solver-ai.onrender.com/heartbeat.md) | Step-by-step agent loop to follow until report is delivered |

### 1. Register your agent

```bash
curl -X POST https://natural-solver-ai.onrender.com/api/agents/register \
  -H "Content-Type: application/json" \
  -d '{"name": "MyAgent", "description": "What I do"}'
```

Response includes an `api_key` (save it — it cannot be retrieved later) and a `claim_url` to share with your human for ownership verification.

> The `api_key` is your agent identity token — it has nothing to do with StackAI credentials, which are handled server-side.

### 2. Submit an optimization problem

Default provider is **OptiMATE** (no extra setup). StackAI is an optional alternative.

```bash
curl -X POST https://natural-solver-ai.onrender.com/api/runs \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F "prompt=Minimize total delivery cost across 10 vehicles serving 50 customers..."
```

Optionally attach data files or select a provider:

```bash
  -F "files=@data.csv" \
  -F "provider=stackai"
```

| Provider | Description | Default? |
|---|---|---|
| `optimate` | Full local multi-agent solver pipeline | Yes |
| `stackai` | Cloud AI consulting analysis | No |

Returns `{ job_id, status: "running", poll_url }` immediately (<1 s).

### 3. Poll for results

```bash
curl https://natural-solver-ai.onrender.com/api/runs/JOB_ID \
  -H "Authorization: Bearer YOUR_API_KEY"
```

Poll every 5 seconds. Expected wait: 2–8 min (OptiMATE) · up to 10 min (StackAI).

When done, `status` becomes `"done"` and `output` contains the full Markdown report (executive summary, LaTeX formulation, results, recommendations).

### 4. Check available providers

```bash
curl https://natural-solver-ai.onrender.com/api/providers
```

All endpoints except `/api/agents/register` and `/api/providers` require `Authorization: Bearer YOUR_API_KEY`.

---

## Local Development

```bash
# Backend (terminal 1)
cd backend
npm install
cp .env.example .env   # fill in Stack AI keys + Upstash credentials
node --env-file=.env server.js

# Frontend (terminal 2)
cd ..
npm install
VITE_API_URL=http://localhost:3001 npm run dev
```

The backend falls back to an in-memory job store if Redis env vars are absent, so local dev works without Upstash.
