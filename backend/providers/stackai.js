// StackAI provider adapter
export const id = "stackai";
export const label = "StackAI";

export const isAvailable = () =>
  !!(process.env.STACK_AI_PUBLIC_KEY && process.env.STACK_AI_ORG_ID && process.env.STACK_AI_FLOW_ID);

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

export async function runJob({ jobId, prompt, files, setJob }) {
  const publicKey = process.env.STACK_AI_PUBLIC_KEY;
  const orgId     = process.env.STACK_AI_ORG_ID;
  const flowId    = process.env.STACK_AI_FLOW_ID;
  const userId    = crypto.randomUUID();
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
      `https://api.stack-ai.com/inference/v0/run/${flowId}/${orgId}`,
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
    "Math formatting rules (strictly required):",
    "- Wrap ALL mathematical expressions in LaTeX delimiters.",
    "- Inline math: $x_i$, $\\sum_i$, $\\leq$, etc.",
    "- Block math (own line, centered): $$\\text{Maximize} \\sum_{i=1}^{n} p_i x_i$$",
    "- Never write raw math without delimiters (e.g. never write 'sum_i p_i x_i', always '$$\\sum_i p_i x_i$$').",
    "- Use standard LaTeX notation: \\sum, \\leq, \\geq, \\cdot, \\in, \\forall, \\text{}, etc.",
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
