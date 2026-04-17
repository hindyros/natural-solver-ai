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
