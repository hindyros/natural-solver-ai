import express from "express";
import cors from "cors";
import multer from "multer";

const app = express();
const upload = multer({ storage: multer.memoryStorage() });

app.use(cors());

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

  const files = req.files ?? [];
  const userId = crypto.randomUUID();

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
        return res.status(502).json({
          error: `File upload failed for "${file.originalname}": ${detail}`,
        });
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
          "in-0": prompt,
          "doc-0": [],
          user_id: userId,
        }),
      },
    );

    if (!runRes.ok) {
      const detail = await runRes.text();
      return res.status(502).json({ error: `Flow run failed: ${detail}` });
    }

    const result = await runRes.json();
    const output =
      result?.outputs?.["out-0"] ?? JSON.stringify(result, null, 2);

    return res.json({ output });
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Internal server error";
    return res.status(500).json({ error: message });
  }
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Backend listening on port ${PORT}`);
});
