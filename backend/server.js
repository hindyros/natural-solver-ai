import express from "express";
import cors from "cors";
import multer from "multer";
import { Redis } from "@upstash/redis";

const app = express();
const upload = multer({ storage: multer.memoryStorage() });

app.use(cors());
app.set("etag", false);
app.use("/api", (_req, res, next) => {
  res.set("Cache-Control", "no-store, no-cache, must-revalidate, proxy-revalidate");
  res.set("Pragma", "no-cache");
  res.set("Expires", "0");
  next();
});

// ---------------------------------------------------------------------------
// Job store — Redis (persistent across restarts, survives Render cold starts)
// Falls back to in-memory Map if Redis env vars are not set (local dev).
// ---------------------------------------------------------------------------
const JOB_TTL_SECONDS = 3600; // jobs expire after 1 hour
const STUCK_JOB_TIMEOUT_MS = 330_000; // mark as error if running > 5.5 min

let redis = null;
if (process.env.UPSTASH_REDIS_REST_URL && process.env.UPSTASH_REDIS_REST_TOKEN) {
  redis = new Redis({
    url: process.env.UPSTASH_REDIS_REST_URL,
    token: process.env.UPSTASH_REDIS_REST_TOKEN,
  });
  console.log("Using Redis for job storage.");
} else {
  console.warn("Redis env vars not set — falling back to in-memory job store (not suitable for production).");
}

const memoryJobs = new Map(); // fallback only

async function getJob(jobId) {
  if (redis) return redis.get(`job:${jobId}`);
  return memoryJobs.get(jobId) ?? null;
}

async function setJob(jobId, data) {
  if (redis) return redis.set(`job:${jobId}`, data, { ex: JOB_TTL_SECONDS });
  memoryJobs.set(jobId, data);
}

async function deleteJob(jobId) {
  if (redis) return redis.del(`job:${jobId}`);
  memoryJobs.delete(jobId);
}

// ---------------------------------------------------------------------------

app.get("/health", (_req, res) => {
  res.json({ ok: true });
});

app.post("/api/stack-run", upload.array("files"), async (req, res) => {
  const publicKey = process.env.STACK_AI_PUBLIC_KEY;
  const orgId = process.env.STACK_AI_ORG_ID;
  const flowId = process.env.STACK_AI_FLOW_ID;

  if (!publicKey || !orgId || !flowId) {
    return res
      .status(500)
      .json({ error: "Server misconfigured: missing Stack AI credentials" });
  }

  const prompt = req.body?.prompt ?? req.query?.prompt;
  if (!prompt?.trim()) {
    return res.status(400).json({ error: "Prompt is required" });
  }

  const files = (req.files ?? []).map((f) => ({
    buffer: Buffer.from(f.buffer),
    originalname: f.originalname,
  }));

  const jobId = crypto.randomUUID();
  await setJob(jobId, { status: "running", startedAt: Date.now() });

  res.json({ jobId });

  runJob({ jobId, prompt, files, publicKey, orgId, flowId });
});

app.get("/api/status/:jobId", async (req, res) => {
  const job = await getJob(req.params.jobId);

  if (!job) {
    return res.status(404).json({ error: "Job not found" });
  }

  // Detect stuck jobs: if still "running" after STUCK_JOB_TIMEOUT_MS, mark as error
  if (job.status === "running" && Date.now() - job.startedAt > STUCK_JOB_TIMEOUT_MS) {
    const updated = { ...job, status: "error", error: "Job timed out — please try again." };
    await setJob(req.params.jobId, updated);
    return res.json(updated);
  }

  res.json(job);
});

// ---------------------------------------------------------------------------
// Timeouts
// ---------------------------------------------------------------------------
const UPLOAD_TIMEOUT_MS = 60_000;   // 60s per file upload
const RUN_TIMEOUT_MS   = 270_000;   // 4.5 min for the StackAI flow

async function fetchWithTimeout(url, options, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

// ---------------------------------------------------------------------------

async function runJob({ jobId, prompt, files, publicKey, orgId, flowId }) {
  const userId = crypto.randomUUID();
  const consultantPrompt = buildConsultantPrompt(prompt);

  try {
    for (const file of files) {
      const form = new FormData();
      form.append("file", new Blob([file.buffer]), file.originalname);

      const uploadUrl = new URL(
        "https://api.stack-ai.com/upload_to_supabase_user",
      );
      uploadUrl.searchParams.set("org", orgId);
      uploadUrl.searchParams.set("user_id", userId);
      uploadUrl.searchParams.set("flow_id", flowId);
      uploadUrl.searchParams.set("node_id", "doc-0");

      const uploadRes = await fetchWithTimeout(
        uploadUrl.toString(),
        { method: "POST", headers: { Authorization: `Bearer ${publicKey}` }, body: form },
        UPLOAD_TIMEOUT_MS,
      );

      if (!uploadRes.ok) {
        const detail = await uploadRes.text();
        await setJob(jobId, {
          status: "error",
          error: `File upload failed for "${file.originalname}": ${detail}`,
        });
        return;
      }
    }

    const runRes = await fetchWithTimeout(
      `https://api.stack-ai.com/inference/v0/run/${orgId}/${flowId}`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${publicKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          "in-0": consultantPrompt,
          "doc-0": [],
          user_id: userId,
        }),
      },
      RUN_TIMEOUT_MS,
    );

    if (!runRes.ok) {
      const detail = await runRes.text();
      await setJob(jobId, { status: "error", error: `Flow run failed: ${detail}` });
      return;
    }

    const result = await runRes.json();
    const output =
      result?.outputs?.["out-0"] ?? JSON.stringify(result, null, 2);

    await setJob(jobId, { status: "done", output });
  } catch (err) {
    const message = err?.name === "AbortError"
      ? "Request timed out — StackAI took too long to respond. Please try again."
      : err instanceof Error ? err.message : "Internal server error";
    await setJob(jobId, { status: "error", error: message });
  }
}

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Backend listening on port ${PORT}`);
});

function buildConsultantPrompt(userPrompt) {
  return [
    "You are a senior optimization consultant.",
    "Return ONLY valid GitHub-flavored Markdown.",
    "Write a polished consulting report with clear section headers and concise prose.",
    "Use this exact top-level structure:",
    "# Executive Summary",
    "# Problem Definition",
    "# Optimization Formulation",
    "# Solution Approach",
    "# Results & Business Impact",
    "# Implementation Roadmap",
    "# Risks & Assumptions",
    "# Next Steps",
    "Formatting requirements:",
    "- Use Markdown tables for key metrics, assumptions, constraints, and roadmap.",
    "- Use bullet points for recommendations and risks.",
    "- Avoid raw JSON unless explicitly requested.",
    "- Keep formulas readable with plain-text math if needed.",
    "- Do NOT use any emojis or emoticons anywhere in the report.",
    "",
    "Client problem:",
    userPrompt,
  ].join("\n");
}
