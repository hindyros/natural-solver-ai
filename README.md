# Op-Σra — AI Optimization Consulting

Vite + React frontend with a standalone Express backend that proxies Stack AI.

## Architecture

```
Browser  ──POST /api/stack-run──▸  Express backend (Render)  ──▸  Stack AI
                                        │
                                        ├─ upload files (upload_to_supabase_user)
                                        └─ run flow   (inference/v0/run)
```

API keys live **only on the backend**. The frontend never sees them.

## Deploy the Backend on Render

1. Go to [render.com/new](https://render.com/new) → **Blueprint** → connect this repo
2. Render auto-reads `render.yaml` and creates the service
3. Fill in the three env vars when prompted:
   - `STACK_AI_PUBLIC_KEY`
   - `STACK_AI_ORG_ID`
   - `STACK_AI_FLOW_ID`
4. Deploy — copy the URL (e.g. `https://natural-solver-backend.onrender.com`)

## Deploy the Frontend on Vercel

1. Go to [vercel.com/new](https://vercel.com/new) → import this repo
2. Add env var: `VITE_API_URL` = your Render backend URL (no trailing slash)
3. Deploy

## Local Development

```bash
# Backend (terminal 1)
cd backend
npm install
cp .env.example .env   # fill in your Stack AI keys
node --env-file=.env server.js

# Frontend (terminal 2)
npm install
VITE_API_URL=http://localhost:3001 npm run dev
```
