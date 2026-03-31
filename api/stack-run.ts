export const config = {
  runtime: "edge",
};

export default async function handler(request: Request): Promise<Response> {
  if (request.method !== "POST") {
    return json({ error: "Method not allowed" }, 405);
  }

  const publicKey = process.env.STACK_AI_PUBLIC_KEY;
  const orgId = process.env.STACK_AI_ORG_ID;
  const flowId = process.env.STACK_AI_FLOW_ID;

  if (!publicKey || !orgId || !flowId) {
    return json({ error: "Server misconfigured: missing Stack AI credentials" }, 500);
  }

  try {
    const formData = await request.formData();
    const prompt = formData.get("prompt") as string;
    const files = formData.getAll("files") as File[];

    if (!prompt?.trim()) {
      return json({ error: "Prompt is required" }, 400);
    }

    const userId = crypto.randomUUID();

    for (const file of files) {
      const uploadForm = new FormData();
      uploadForm.append("file", file);

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
        return json({ error: `File upload failed for "${file.name}": ${detail}` }, 502);
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
      return json({ error: `Flow run failed: ${detail}` }, 502);
    }

    const result = await runRes.json();
    const output: string =
      result?.outputs?.["out-0"] ?? JSON.stringify(result, null, 2);

    return json({ output });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Internal server error";
    return json({ error: message }, 500);
  }
}

function json(body: Record<string, unknown>, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
