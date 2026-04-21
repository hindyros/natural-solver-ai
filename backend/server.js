import express from "express";
import cors from "cors";
import multer from "multer";
import { Redis } from "@upstash/redis";
import { getProvider, listProviders } from "./providers/index.js";

const app = express();
const upload = multer({ storage: multer.memoryStorage() });

app.use(cors());
app.use(express.json());
app.set("etag", false);
app.use("/api", (_req, res, next) => {
  res.set("Cache-Control", "no-store, no-cache, must-revalidate, proxy-revalidate");
  res.set("Pragma", "no-cache");
  res.set("Expires", "0");
  next();
});

// ---------------------------------------------------------------------------
// Job store — Upstash Redis with in-memory fallback for local dev
// ---------------------------------------------------------------------------
const JOB_TTL_SECONDS      = 3600;
const AGENT_TTL_SECONDS    = 30 * 24 * 3600; // 30 days
const STUCK_JOB_TIMEOUT_MS = 960_000; // 16 min

let redis = null;
if (process.env.UPSTASH_REDIS_REST_URL && process.env.UPSTASH_REDIS_REST_TOKEN) {
  redis = new Redis({
    url: process.env.UPSTASH_REDIS_REST_URL,
    token: process.env.UPSTASH_REDIS_REST_TOKEN,
  });
  console.log("Using Redis for job storage.");
} else {
  console.warn("Redis env vars not set — falling back to in-memory job store.");
}

const memoryJobs   = new Map();
const memoryAgents = new Map();

async function getJob(jobId) {
  if (redis) return redis.get(`job:${jobId}`);
  return memoryJobs.get(jobId) ?? null;
}

async function setJob(jobId, data) {
  if (redis) return redis.set(`job:${jobId}`, data, { ex: JOB_TTL_SECONDS });
  memoryJobs.set(jobId, data);
}

async function getAgent(apiKey) {
  if (redis) return redis.get(`agent:${apiKey}`);
  return memoryAgents.get(apiKey) ?? null;
}

async function setAgent(apiKey, data) {
  if (redis) return redis.set(`agent:${apiKey}`, data, { ex: AGENT_TTL_SECONDS });
  memoryAgents.set(apiKey, data);
}

async function getAgentByClaimToken(claimToken) {
  if (redis) {
    const apiKey = await redis.get(`claim:${claimToken}`);
    if (!apiKey) return null;
    return redis.get(`agent:${apiKey}`);
  }
  for (const agent of memoryAgents.values()) {
    if (agent.claimToken === claimToken) return agent;
  }
  return null;
}

function generateApiKey() {
  return `opera_${crypto.randomUUID().replace(/-/g, "")}`;
}

function generateClaimToken() {
  return `claim_${crypto.randomUUID().replace(/-/g, "")}`;
}

// ---------------------------------------------------------------------------
// Auth middleware
// ---------------------------------------------------------------------------
async function requireAuth(req, res, next) {
  const header = req.headers.authorization;
  const apiKey = header?.replace("Bearer ", "").trim();
  if (!apiKey) {
    return res.status(401).json({
      success: false,
      error: "Missing API key",
      hint: "Include the header: Authorization: Bearer YOUR_API_KEY",
    });
  }
  const agent = await getAgent(apiKey);
  if (!agent) {
    return res.status(401).json({
      success: false,
      error: "Invalid API key",
      hint: "Register at POST /api/agents/register to get an API key",
    });
  }
  await setAgent(apiKey, { ...agent, lastActive: Date.now() });
  req.agent = agent;
  next();
}

// ---------------------------------------------------------------------------
// Protocol files — served as static text at root paths
// ---------------------------------------------------------------------------

app.get("/skill.md", (req, res) => {
  const backendUrl  = process.env.APP_URL || `http://localhost:${process.env.PORT || 3001}`;
  const frontendUrl = process.env.FRONTEND_URL || backendUrl;

  const md = `---
name: op-era
version: 1.0.0
description: AI-powered optimization formulation engine — turns natural-language business problems into consultant-grade mathematical optimization reports.
homepage: ${frontendUrl}
metadata: {"openclaw":{"emoji":"Σ","category":"analytics","api_base":"${backendUrl}/api"}}
---

# Op-Era — Optimization Formulation Engine

Op-Era takes a natural-language description of an optimization problem (routing, scheduling, resource allocation, supply chain, etc.) and returns a polished consulting-grade report with the mathematical formulation, solved results, and business recommendations.

---

## Step 1: Register your agent

\`\`\`bash
curl -X POST ${backendUrl}/api/agents/register \\
  -H "Content-Type: application/json" \\
  -d '{"name": "YourAgentName", "description": "What you do"}'
\`\`\`

**Response:**
\`\`\`json
{
  "success": true,
  "data": {
    "agent": {
      "name": "YourAgentName",
      "api_key": "opera_...",
      "claim_url": "${frontendUrl}/claim/claim_..."
    },
    "important": "SAVE YOUR API KEY! You cannot retrieve it later."
  }
}
\`\`\`

**Save your api_key immediately.** Send the claim_url to your human so they can verify ownership.

---

## Step 2: Get claimed by your human

Share the \`claim_url\` with your human. They click it — no login required. That's all.

---

## Step 3: Submit an optimization problem

\`\`\`bash
curl -X POST ${backendUrl}/api/runs \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -F "prompt=Minimize total delivery cost across 10 vehicles serving 50 customers. Each vehicle starts and ends at a central depot, has a capacity of 500 kg, and all deliveries must arrive within their 2-hour time windows." \\
  -F "provider=optimate"
\`\`\`

Optionally attach a CSV data file (e.g. customers, distances, costs):
\`\`\`bash
curl -X POST ${backendUrl}/api/runs \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -F "prompt=Optimize staff scheduling to minimize overtime cost while meeting demand" \\
  -F "files=@schedule_data.csv" \\
  -F "provider=optimate"
\`\`\`

**Available providers:**
- \`optimate\` — Full multi-agent pipeline: mathematical formulation, solver execution, detailed report
- \`stackai\` — Cloud AI consulting analysis

**Response (202 Accepted):**
\`\`\`json
{
  "success": true,
  "data": {
    "job_id": "uuid-...",
    "status": "running",
    "poll_url": "/api/runs/uuid-...",
    "hint": "Poll GET /api/runs/uuid-... every 5 seconds until status is done or error"
  }
}
\`\`\`

---

## Step 4: Poll for results

\`\`\`bash
curl ${backendUrl}/api/runs/JOB_ID \\
  -H "Authorization: Bearer YOUR_API_KEY"
\`\`\`

**While running:**
\`\`\`json
{"success": true, "data": {"job_id": "...", "status": "running"}}
\`\`\`

**When done:**
\`\`\`json
{
  "success": true,
  "data": {
    "job_id": "...",
    "status": "done",
    "output": "# Optimization Analysis Report\\n\\n## Executive Summary\\n..."
  }
}
\`\`\`

The \`output\` field is a full Markdown report including:
- Executive summary with business impact
- Mathematical formulation (LaTeX)
- Solution results and key decisions
- Numbered recommendations
- Assumptions and limitations

**On error:**
\`\`\`json
{"success": true, "data": {"status": "error", "error": "description of what went wrong"}}
\`\`\`

Poll every 5 seconds. The OptiMATE pipeline takes 2–8 minutes. StackAI may take up to 10 minutes.

---

## Step 5: Check available providers

\`\`\`bash
curl ${backendUrl}/api/providers
\`\`\`

\`\`\`json
[
  {"id": "optimate", "label": "OptiMATE", "available": true},
  {"id": "stackai", "label": "StackAI", "available": true}
]
\`\`\`

---

## Authentication

All endpoints except \`/api/agents/register\` and \`/api/providers\` require:
\`\`\`
Authorization: Bearer YOUR_API_KEY
\`\`\`

---

## Response format

**Success:** \`{"success": true, "data": {...}}\`

**Error:** \`{"success": false, "error": "message", "hint": "what to do"}\`

---

## Tips for agents

- If your human hasn't described their problem yet, ask them: "What optimization problem would you like me to solve? (e.g. minimize cost, maximize profit, optimize scheduling)"
- If they have data files (CSV, Excel), ask them to provide the file path so you can attach it.
- The report output is Markdown — you can paste it directly to your human or summarize the key findings.
- If a job errors, retry once with the same prompt before escalating to your human.
`;

  res.set("Content-Type", "text/markdown; charset=utf-8");
  res.send(md);
});

app.get("/heartbeat.md", (req, res) => {
  const backendUrl = process.env.APP_URL || `http://localhost:${process.env.PORT || 3001}`;

  const md = `# Op-Era — Heartbeat

**Keep running this loop until you've delivered an optimization report to your human.**

If anything goes wrong that you can't resolve, message your human and ask what to do. Never silently fail.

---

## Your Goal

Submit your human's optimization problem to Op-Era and deliver the resulting consulting report back to them.

**Done** = your human has received a complete report with results and recommendations.

---

## Loop

### Step 1: Check your setup

- Am I registered? Do I have an api_key saved?
  - If no → register at \`POST ${backendUrl}/api/agents/register\`
- Has my human claimed me? (If not, send them the claim_url and wait.)
- Do I know what optimization problem my human wants solved?
  - If no → message your human: *"What optimization problem would you like me to solve? Describe it in plain language (e.g. minimize delivery cost, schedule staff efficiently, allocate budget optimally). If you have data files, share them too."*

### Step 2: Submit the problem

- Call \`POST ${backendUrl}/api/runs\` with the problem description
- Attach any data files your human provided
- Save the \`job_id\` from the response

### Step 3: Poll for completion

- Call \`GET ${backendUrl}/api/runs/{job_id}\` every 5 seconds
- Continue until \`status\` is \`"done"\` or \`"error"\`
- Expected wait: 2–8 minutes for OptiMATE, up to 10 minutes for StackAI

### Step 4: Deliver results

- If \`status === "done"\`: send the \`output\` (Markdown report) to your human
  - Highlight: the objective value, top 3 recommendations, and any key constraints that were binding
- If \`status === "error"\`: tell your human what failed and ask if they want to retry or rephrase the problem

### Step 5: Check if done

- Has your human confirmed they received and understand the report?
- If yes → you're done
- If they want another problem solved → go back to Step 2

---

## Error Handling

| Problem | Action |
|---------|--------|
| Registration fails | Check name uniqueness; try a different name |
| Job returns error | Retry once; if it fails again, tell your human |
| Job stuck > 15 min | Treat as timeout; tell your human and offer to retry |
| Human unresponsive | Wait up to 24h before re-prompting |

---

## Key endpoints

- Register: \`POST ${backendUrl}/api/agents/register\`
- Submit job: \`POST ${backendUrl}/api/runs\`
- Poll status: \`GET ${backendUrl}/api/runs/{job_id}\`
- List providers: \`GET ${backendUrl}/api/providers\`
`;

  res.set("Content-Type", "text/markdown; charset=utf-8");
  res.send(md);
});

app.get("/skill.json", (req, res) => {
  const backendUrl  = process.env.APP_URL || `http://localhost:${process.env.PORT || 3001}`;
  const frontendUrl = process.env.FRONTEND_URL || backendUrl;
  res.json({
    name: "op-era",
    version: "1.0.0",
    description: "Turn any optimization problem into a consultant-grade analysis report using AI-driven mathematical formulation and solving.",
    homepage: frontendUrl,
    metadata: {
      openclaw: {
        emoji: "Σ",
        category: "analytics",
        api_base: `${backendUrl}/api`,
      },
    },
  });
});

// ---------------------------------------------------------------------------
// Agent registration & claim
// ---------------------------------------------------------------------------

app.post("/api/agents/register", async (req, res) => {
  const { name, description } = req.body ?? {};
  if (!name?.trim() || !description?.trim()) {
    return res.status(400).json({
      success: false,
      error: "Missing fields",
      hint: '"name" and "description" are both required',
    });
  }

  const apiKey     = generateApiKey();
  const claimToken = generateClaimToken();
  const frontendUrl = process.env.FRONTEND_URL || process.env.APP_URL || "http://localhost:3000";

  const agent = {
    name: name.trim(),
    description: description.trim(),
    apiKey,
    claimToken,
    claimStatus: "pending_claim",
    createdAt: Date.now(),
    lastActive: Date.now(),
  };

  await setAgent(apiKey, agent);
  if (redis) await redis.set(`claim:${claimToken}`, apiKey, { ex: AGENT_TTL_SECONDS });

  return res.status(201).json({
    success: true,
    data: {
      agent: {
        name: agent.name,
        api_key: apiKey,
        claim_url: `${frontendUrl}/claim/${claimToken}`,
      },
      important: "SAVE YOUR API KEY! You cannot retrieve it later.",
    },
  });
});

// Claim verification — called by frontend after human clicks the claim link
app.post("/api/agents/claim/:token", async (req, res) => {
  const agent = await getAgentByClaimToken(req.params.token);
  if (!agent) {
    return res.status(404).json({ success: false, error: "Claim token not found or already used" });
  }
  const updated = { ...agent, claimStatus: "claimed", claimedAt: Date.now() };
  await setAgent(agent.apiKey, updated);
  return res.json({ success: true, data: { name: agent.name, message: "Agent successfully claimed!" } });
});

// ---------------------------------------------------------------------------
// Agent-authenticated optimization runs
// ---------------------------------------------------------------------------

app.post("/api/runs", requireAuth, upload.array("files"), async (req, res) => {
  const prompt = req.body?.prompt ?? req.query?.prompt;
  if (!prompt?.trim()) {
    return res.status(400).json({
      success: false,
      error: "Prompt is required",
      hint: 'Include a "prompt" field describing your optimization problem in plain language',
    });
  }

  const providerId = (req.body?.provider || process.env.BACKEND_PROVIDER || "stackai").toLowerCase();
  const provider   = getProvider(providerId);

  if (!provider || !provider.isAvailable()) {
    const available = listProviders().filter((p) => p.available).map((p) => p.id);
    return res.status(400).json({
      success: false,
      error: `Provider "${providerId}" is not available`,
      hint: `Available providers: ${available.join(", ") || "none configured"}`,
    });
  }

  const files = (req.files ?? []).map((f) => ({
    buffer: Buffer.from(f.buffer),
    originalname: f.originalname,
  }));

  const jobId = crypto.randomUUID();
  await setJob(jobId, {
    status: "running",
    startedAt: Date.now(),
    provider: providerId,
    agentName: req.agent.name,
  });

  provider.runJob({ jobId, prompt, files, setJob });

  const backendUrl = process.env.APP_URL || `http://localhost:${process.env.PORT || 3001}`;
  return res.status(202).json({
    success: true,
    data: {
      job_id: jobId,
      status: "running",
      poll_url: `${backendUrl}/api/runs/${jobId}`,
      hint: `Poll GET /api/runs/${jobId} every 5 seconds until status is "done" or "error". Expected wait: 2–8 minutes.`,
    },
  });
});

app.get("/api/runs/:jobId", requireAuth, async (req, res) => {
  const job = await getJob(req.params.jobId);
  if (!job) {
    return res.status(404).json({
      success: false,
      error: "Job not found",
      hint: "Jobs expire after 1 hour. Submit a new run.",
    });
  }

  if (job.status === "running" && Date.now() - job.startedAt > STUCK_JOB_TIMEOUT_MS) {
    const updated = { ...job, status: "error", error: "Job timed out — please submit again." };
    await setJob(req.params.jobId, updated);
    return res.json({ success: true, data: { job_id: req.params.jobId, ...updated } });
  }

  return res.json({ success: true, data: { job_id: req.params.jobId, ...job } });
});

// ---------------------------------------------------------------------------
// Existing human-facing routes (unchanged)
// ---------------------------------------------------------------------------

app.get("/health", (_req, res) => {
  const defaultProvider = process.env.BACKEND_PROVIDER ?? "stackai";
  res.json({ ok: true, provider: defaultProvider, providers: listProviders() });
});

app.get("/api/providers", (_req, res) => {
  res.json(listProviders());
});

app.post("/api/stack-run", upload.array("files"), async (req, res) => {
  const prompt = req.body?.prompt ?? req.query?.prompt;
  if (!prompt?.trim()) {
    return res.status(400).json({ error: "Prompt is required" });
  }

  const providerId = (req.body?.provider || process.env.BACKEND_PROVIDER || "stackai").toLowerCase();
  const provider = getProvider(providerId);

  if (!provider) {
    return res.status(400).json({ error: `Unknown provider: "${providerId}"` });
  }
  if (!provider.isAvailable()) {
    return res.status(500).json({ error: `Provider "${providerId}" is not configured on this server.` });
  }

  const files = (req.files ?? []).map((f) => ({
    buffer: Buffer.from(f.buffer),
    originalname: f.originalname,
  }));

  const jobId = crypto.randomUUID();
  await setJob(jobId, { status: "running", startedAt: Date.now(), provider: providerId });
  res.json({ jobId });

  provider.runJob({ jobId, prompt, files, setJob });
});

app.get("/api/status/:jobId", async (req, res) => {
  const job = await getJob(req.params.jobId);

  if (!job) {
    return res.status(404).json({ error: "Job not found" });
  }

  if (job.status === "running" && Date.now() - job.startedAt > STUCK_JOB_TIMEOUT_MS) {
    const updated = { ...job, status: "error", error: "Job timed out — please try again." };
    await setJob(req.params.jobId, updated);
    return res.json(updated);
  }

  res.json(job);
});

// ---------------------------------------------------------------------------

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Backend listening on port ${PORT}`);
  console.log("Available providers:", listProviders().map((p) => `${p.id} (${p.available ? "ready" : "not configured"})`).join(", "));
});
