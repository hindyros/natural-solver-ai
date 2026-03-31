import type { VercelRequest, VercelResponse } from "@vercel/node";
import { Readable } from "node:stream";
import { Buffer } from "node:buffer";

export const config = {
  api: { bodyParser: false },
  maxDuration: 600,
};

export default async function handler(
  req: VercelRequest,
  res: VercelResponse,
): Promise<void> {
  if (req.method !== "POST") {
    res.status(405).json({ error: "Method not allowed" });
    return;
  }

  const publicKey = process.env.STACK_AI_PUBLIC_KEY;
  const orgId = process.env.STACK_AI_ORG_ID;
  const flowId = process.env.STACK_AI_FLOW_ID;

  if (!publicKey || !orgId || !flowId) {
    res.status(500).json({ error: "Server misconfigured: missing Stack AI credentials" });
    return;
  }

  try {
    const { prompt, files } = await parseMultipart(req);

    if (!prompt?.trim()) {
      res.status(400).json({ error: "Prompt is required" });
      return;
    }

    const userId = crypto.randomUUID();

    for (const file of files) {
      const uploadForm = new FormData();
      uploadForm.append("file", new Blob([file.buffer]), file.name);

      const uploadUrl = new URL("https://api.stack-ai.com/upload_to_supabase_user");
      uploadUrl.searchParams.set("org", orgId);
      uploadUrl.searchParams.set("user_id", userId);
      uploadUrl.searchParams.set("flow_id", flowId);
      uploadUrl.searchParams.set("node_id", "doc-0");

      const uploadRes = await fetch(uploadUrl.toString(), {
        method: "POST",
        headers: { Authorization: `Bearer ${publicKey}` },
        body: uploadForm,
      });

      if (!uploadRes.ok) {
        const detail = await uploadRes.text();
        res.status(502).json({ error: `File upload failed for "${file.name}": ${detail}` });
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
          "in-0": prompt,
          "doc-0": [],
          user_id: userId,
        }),
      },
    );

    if (!runRes.ok) {
      const detail = await runRes.text();
      res.status(502).json({ error: `Flow run failed: ${detail}` });
      return;
    }

    const result = await runRes.json();
    const output: string =
      result?.outputs?.["out-0"] ?? JSON.stringify(result, null, 2);

    res.status(200).json({ output });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Internal server error";
    res.status(500).json({ error: message });
  }
}

interface UploadedFile {
  name: string;
  buffer: Buffer;
}

async function parseMultipart(
  req: VercelRequest,
): Promise<{ prompt: string; files: UploadedFile[] }> {
  const busboy = (await import("busboy")).default;

  return new Promise((resolve, reject) => {
    const files: UploadedFile[] = [];
    let prompt = "";

    const bb = busboy({ headers: req.headers as Record<string, string> });

    bb.on("field", (name: string, val: string) => {
      if (name === "prompt") prompt = val;
    });

    bb.on("file", (fieldname: string, stream: Readable, info: { filename: string }) => {
      const chunks: Buffer[] = [];
      stream.on("data", (chunk: Buffer) => chunks.push(chunk));
      stream.on("end", () => {
        files.push({ name: info.filename, buffer: Buffer.concat(chunks) });
      });
    });

    bb.on("close", () => resolve({ prompt, files }));
    bb.on("error", reject);

    req.pipe(bb);
  });
}
