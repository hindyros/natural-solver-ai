import express from "express";
import cors from "cors";
import multer from "multer";

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

const jobs = new Map();

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
  jobs.set(jobId, { status: "running" });

  res.json({ jobId });

  runJob({ jobId, prompt, files, publicKey, orgId, flowId });
});

app.get("/api/status/:jobId", (req, res) => {
  const job = jobs.get(req.params.jobId);

  if (!job) {
    return res.status(404).json({ error: "Job not found" });
  }

  res.json(job);

  if (job.status !== "running") {
    setTimeout(() => jobs.delete(req.params.jobId), 60_000);
  }
});

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

      const uploadRes = await fetch(uploadUrl.toString(), {
        method: "POST",
        headers: { Authorization: `Bearer ${publicKey}` },
        body: form,
      });

      if (!uploadRes.ok) {
        const detail = await uploadRes.text();
        jobs.set(jobId, {
          status: "error",
          error: `File upload failed for "${file.originalname}": ${detail}`,
        });
        return;
      }
    }

    const runRes = await fetch(
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
    );

    if (!runRes.ok) {
      const detail = await runRes.text();
      jobs.set(jobId, { status: "error", error: `Flow run failed: ${detail}` });
      return;
    }

    const result = await runRes.json();
    const output =
      result?.outputs?.["out-0"] ?? JSON.stringify(result, null, 2);

    jobs.set(jobId, { status: "done", output });
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Internal server error";
    jobs.set(jobId, { status: "error", error: message });
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
    "",
    "Client problem:",
    userPrompt,
  ].join("\n");
}
