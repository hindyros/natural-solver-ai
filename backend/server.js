import express from "express";
import cors from "cors";
import multer from "multer";
import { Redis } from "@upstash/redis";
import { spawn } from "child_process";
import { writeFile, readFile, unlink } from "fs/promises";
import { join } from "path";
import { tmpdir } from "os";

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
// Backend provider — set BACKEND_PROVIDER=optimate to use OptiMATE v1-light
// ---------------------------------------------------------------------------
const BACKEND_PROVIDER = (process.env.BACKEND_PROVIDER ?? "stackai").toLowerCase();
console.log(`Backend provider: ${BACKEND_PROVIDER}`);

// ---------------------------------------------------------------------------
// Job store — Redis (persistent across restarts, survives Render cold starts)
// Falls back to in-memory Map if Redis env vars are not set (local dev).
// ---------------------------------------------------------------------------
const JOB_TTL_SECONDS = 3600;
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
  res.json({ ok: true, provider: BACKEND_PROVIDER });
});

app.post("/api/stack-run", upload.array("files"), async (req, res) => {
  const prompt = req.body?.prompt ?? req.query?.prompt;
  if (!prompt?.trim()) {
    return res.status(400).json({ error: "Prompt is required" });
  }

  const files = (req.files ?? []).map((f) => ({
    buffer: Buffer.from(f.buffer),
    originalname: f.originalname,
  }));

  if (BACKEND_PROVIDER === "stackai") {
    const publicKey = process.env.STACK_AI_PUBLIC_KEY;
    const orgId     = process.env.STACK_AI_ORG_ID;
    const flowId    = process.env.STACK_AI_FLOW_ID;

    if (!publicKey || !orgId || !flowId) {
      return res.status(500).json({ error: "Server misconfigured: missing Stack AI credentials" });
    }

    const jobId = crypto.randomUUID();
    await setJob(jobId, { status: "running", startedAt: Date.now() });
    res.json({ jobId });
    runStackAIJob({ jobId, prompt, files, publicKey, orgId, flowId });

  } else if (BACKEND_PROVIDER === "optimate") {
    const optimateDir = process.env.OPTIMATE_DIR;
    const optimatePython = process.env.OPTIMATE_PYTHON ?? "python3";
    const optimateLlmProvider = process.env.OPTIMATE_LLM_PROVIDER ?? "openai";
    const optimatePythonPath = process.env.OPTIMATE_PYTHONPATH ?? "";

    if (!optimateDir) {
      return res.status(500).json({ error: "Server misconfigured: OPTIMATE_DIR is not set" });
    }

    const jobId = crypto.randomUUID();
    await setJob(jobId, { status: "running", startedAt: Date.now() });
    res.json({ jobId });
    runOptimateJob({ jobId, prompt, files, optimateDir, optimatePython, optimateLlmProvider, optimatePythonPath });

  } else {
    return res.status(500).json({ error: `Unknown BACKEND_PROVIDER: "${BACKEND_PROVIDER}"` });
  }
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
// StackAI backend
// ---------------------------------------------------------------------------
const UPLOAD_TIMEOUT_MS = 60_000;
const RUN_TIMEOUT_MS    = 900_000;

async function fetchWithTimeout(url, options, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

async function runStackAIJob({ jobId, prompt, files, publicKey, orgId, flowId }) {
  const userId = crypto.randomUUID();
  const consultantPrompt = buildConsultantPrompt(prompt);

  try {
    for (const file of files) {
      const form = new FormData();
      form.append("file", new Blob([file.buffer]), file.originalname);

      const uploadUrl = new URL("https://api.stack-ai.com/upload_to_supabase_user");
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
        await setJob(jobId, { status: "error", error: `File upload failed for "${file.originalname}": ${detail}` });
        return;
      }
    }

    const runRes = await fetchWithTimeout(
      `https://api.stack-ai.com/inference/v0/run/${orgId}/${flowId}`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${publicKey}`, "Content-Type": "application/json" },
        body: JSON.stringify({ "in-0": consultantPrompt, "doc-0": [], user_id: userId }),
      },
      RUN_TIMEOUT_MS,
    );

    if (!runRes.ok) {
      const detail = await runRes.text();
      await setJob(jobId, { status: "error", error: `Flow run failed: ${detail}` });
      return;
    }

    const result = await runRes.json();
    const output = result?.outputs?.["out-0"] ?? JSON.stringify(result, null, 2);
    await setJob(jobId, { status: "done", output });

  } catch (err) {
    const message = err?.name === "AbortError"
      ? "Request timed out — StackAI took too long to respond. Please try again."
      : err instanceof Error ? err.message : "Internal server error";
    await setJob(jobId, { status: "error", error: message });
  }
}

// ---------------------------------------------------------------------------
// OptiMATE v1-light backend
// ---------------------------------------------------------------------------
async function runOptimateJob({ jobId, prompt, files, optimateDir, optimatePython, optimateLlmProvider, optimatePythonPath }) {
  const tempFiles = [];
  console.log(`[OptiMATE] Starting job ${jobId} | python=${optimatePython} | dir=${optimateDir} | provider=${optimateLlmProvider}`);

  try {
    // Write the prompt to a temp .txt file
    const promptFile = join(tmpdir(), `optimate_${jobId}.txt`);
    await writeFile(promptFile, prompt, "utf8");
    tempFiles.push(promptFile);

    // Write any uploaded files to temp (CSV/JSON supported by OptiMATE)
    const dataArgs = [];
    for (const file of files) {
      const tmpPath = join(tmpdir(), `optimate_${jobId}_${file.originalname}`);
      await writeFile(tmpPath, file.buffer);
      tempFiles.push(tmpPath);
      dataArgs.push("--data", tmpPath);
    }

    // Build CLI args: python cli.py run --input <prompt> [--data <f>...] --provider openai
    const args = [
      join(optimateDir, "cli.py"),
      "run",
      "--input", promptFile,
      ...dataArgs,
      "--provider", optimateLlmProvider,
    ];

    // py_packages lives one level above optimate/ (both under project src root)
    const pyPackagesPath = join(optimateDir, "..", "py_packages");
    const subEnv = { ...process.env };
    subEnv.PYTHONPATH = [pyPackagesPath, optimatePythonPath, process.env.PYTHONPATH]
      .filter(Boolean).join(":");

    const output = await spawnAsync(optimatePython, args, {
      cwd: optimateDir,
      env: subEnv,
      timeoutMs: RUN_TIMEOUT_MS,
    });

    // Parse the report path from CLI stdout: "Done! Report: /path/to/report.md"
    const match = output.stdout.match(/Done!\s+Report:\s+(\S+)/);
    if (!match) {
      throw new Error(`OptiMATE did not produce a report.\n\nCLI output:\n${output.stdout}\n${output.stderr}`);
    }

    const reportPath = match[1];
    console.log(`[OptiMATE] Job ${jobId} done — report: ${reportPath}`);
    const report = await readFile(reportPath, "utf8");
    await setJob(jobId, { status: "done", output: report });

  } catch (err) {
    const message = err instanceof Error ? err.message : "OptiMATE pipeline failed";
    console.error(`[OptiMATE] Job ${jobId} FAILED:`, message);
    await setJob(jobId, { status: "error", error: message });
  } finally {
    // Clean up temp files
    for (const f of tempFiles) {
      unlink(f).catch(() => {});
    }
  }
}

function spawnAsync(cmd, args, { cwd, env, timeoutMs }) {
  return new Promise((resolve, reject) => {
    const proc = spawn(cmd, args, { cwd, env });
    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (d) => { stdout += d.toString(); });
    proc.stderr.on("data", (d) => { stderr += d.toString(); });

    const timer = setTimeout(() => {
      proc.kill();
      reject(new Error(`OptiMATE timed out after ${timeoutMs / 1000}s`));
    }, timeoutMs);

    proc.on("close", (code) => {
      clearTimeout(timer);
      if (code === 0) {
        resolve({ stdout, stderr });
      } else {
        reject(new Error(`OptiMATE exited with code ${code}.\n\nstdout:\n${stdout}\n\nstderr:\n${stderr}`));
      }
    });

    proc.on("error", (err) => {
      clearTimeout(timer);
      reject(err);
    });
  });
}

// ---------------------------------------------------------------------------

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
    "- Include 1-2 Mermaid diagrams where they add insight. Use fenced code blocks with the 'mermaid' language tag.",
    "  Good uses: pie chart for resource utilisation, flowchart for solution approach or decision path.",
    "  Example pie chart:",
    "  ```mermaid",
    "  pie title Flour Utilisation",
    '    "Bread" : 40',
    '    "Croissants" : 60',
    "  ```",
    "  Keep diagrams simple and correctly-formed. Only include a diagram if it genuinely aids understanding.",
    "",
    "Client problem:",
    userPrompt,
  ].join("\n");
}
