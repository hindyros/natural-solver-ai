# Op-Σra — AI Optimization Consulting

Vite + React frontend with a standalone Express backend that proxies Stack AI.

## Architecture

```
Browser  ──POST /api/stack-run──▸  Express backend (Railway)  ──▸  Stack AI
                                        │
                                        ├─ upload files (upload_to_supabase_user)
                                        └─ run flow   (inference/v0/run)
```

API keys live **only on the backend** (Railway env vars). The frontend never sees them.

## Repo Structure

```
├── src/              # Vite + React frontend (deployed on Vercel)
├── backend/          # Express backend (deployed on Railway)
│   ├── server.js
│   ├── package.json
│   └── .env.example
├── vercel.json       # SPA routing for Vercel
└── .env.example      # Frontend env (VITE_API_URL)
```

## Backend Environment Variables (set in Railway dashboard)

| Variable | Description |
|---|---|
| `STACK_AI_PUBLIC_KEY` | Stack AI bearer token |
| `STACK_AI_ORG_ID` | Your Stack AI organisation ID |
| `STACK_AI_FLOW_ID` | The flow to execute |

## Frontend Environment Variables (set in Vercel dashboard)

| Variable | Description |
|---|---|
| `VITE_API_URL` | URL of the deployed backend (e.g. `https://xxx.up.railway.app`) |

## Local Development

```bash
# Backend (terminal 1)
cd backend
npm install
cp .env.example .env   # fill in your Stack AI keys
npm start

# Frontend (terminal 2)
npm install
VITE_API_URL=http://localhost:3001 npm run dev
```

## Deploy

### Backend → Railway
1. Go to [railway.app/new](https://railway.app/new) → Deploy from GitHub
2. Set **Root Directory** to `backend`
3. Add the three Stack AI env vars
4. Deploy — note the public URL

### Frontend → Vercel
1. Go to [vercel.com/new](https://vercel.com/new) → Import this repo
2. Add env var: `VITE_API_URL` = your Railway backend URL
3. Deploy
