# Op-Σra — AI Optimization Consulting

Vite + React frontend with a Vercel Edge serverless backend that proxies Stack AI.

## Architecture

```
Browser  ──POST /api/stack-run──▸  Vercel Edge Function  ──▸  Stack AI
                                        │
                                        ├─ upload files (upload_to_supabase_user)
                                        └─ run flow   (inference/v0/run)
```

API keys live **only on the server** (Vercel env vars). The frontend never sees them.

## Environment Variables (set in Vercel dashboard)

| Variable | Description |
|---|---|
| `STACK_AI_PUBLIC_KEY` | Stack AI bearer token |
| `STACK_AI_ORG_ID` | Your Stack AI organisation ID |
| `STACK_AI_FLOW_ID` | The flow to execute |

## Local Development

```bash
npm install

# Option A — full stack via Vercel CLI (recommended)
npx vercel dev

# Option B — frontend only (API calls will fail)
npm run dev
```

## Deploy to Vercel

1. Push this repo to GitHub
2. Import the repo in [vercel.com/new](https://vercel.com/new)
3. Add the three env vars above in **Settings → Environment Variables**
4. Deploy — done
