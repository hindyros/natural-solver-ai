import express from "express";
import cors from "cors";
import multer from "multer";
import { Redis } from "@upstash/redis";
import { getProvider, listProviders } from "./providers/index.js";

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
// Job store — Upstash Redis with in-memory fallback for local dev
// ---------------------------------------------------------------------------
const JOB_TTL_SECONDS    = 3600;
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

const memoryJobs = new Map();

async function getJob(jobId) {
  if (redis) return redis.get(`job:${jobId}`);
  return memoryJobs.get(jobId) ?? null;
}

async function setJob(jobId, data) {
  if (redis) return redis.set(`job:${jobId}`, data, { ex: JOB_TTL_SECONDS });
  memoryJobs.set(jobId, data);
}

// ---------------------------------------------------------------------------
// Routes
// ---------------------------------------------------------------------------

app.get("/health", (_req, res) => {
  const defaultProvider = process.env.BACKEND_PROVIDER ?? "stackai";
  res.json({ ok: true, provider: defaultProvider, providers: listProviders() });
});

// List available providers — frontend uses this to show the selector
app.get("/api/providers", (_req, res) => {
  res.json(listProviders());
});

app.post("/api/stack-run", upload.array("files"), async (req, res) => {
  const prompt = req.body?.prompt ?? req.query?.prompt;
  if (!prompt?.trim()) {
    return res.status(400).json({ error: "Prompt is required" });
  }

  // Provider can be chosen per-request (from body) or fall back to env var
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
