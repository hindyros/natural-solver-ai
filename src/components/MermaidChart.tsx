import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";

mermaid.initialize({
  startOnLoad: false,
  theme: "dark",
  themeVariables: {
    background: "transparent",
    primaryColor: "#22c55e",
    primaryTextColor: "#f8fafc",
    primaryBorderColor: "#22c55e",
    lineColor: "#64748b",
    secondaryColor: "#1e293b",
    tertiaryColor: "#0f172a",
    textColor: "#94a3b8",
    fontSize: "14px",
  },
});

let idCounter = 0;

export default function MermaidChart({ code }: { code: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [error, setError] = useState(false);
  const id = useRef(`mermaid-${++idCounter}`);

  useEffect(() => {
    if (!ref.current) return;
    mermaid
      .render(id.current, code)
      .then(({ svg }) => {
        if (ref.current) ref.current.innerHTML = svg;
      })
      .catch(() => setError(true));
  }, [code]);

  if (error) {
    // Fall back to plain code block
    return (
      <pre className="overflow-x-auto rounded bg-muted p-4 text-xs text-muted-foreground">
        <code>{code}</code>
      </pre>
    );
  }

  return (
    <div
      ref={ref}
      className="my-6 flex justify-center overflow-x-auto rounded border border-border bg-card/50 p-6"
    />
  );
}
