import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Upload, X, Send, FileText, Loader2 } from "lucide-react";
import { toast } from "@/hooks/use-toast";
import MathAnimation from "@/components/MathAnimation";
import { lazy, Suspense } from "react";
const MermaidChart = lazy(() => import("@/components/MermaidChart"));

const Index = () => {
  const [description, setDescription] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [report, setReport] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const reportRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (report && reportRef.current) {
      reportRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [report]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles((prev) => [...prev, ...Array.from(e.target.files!)]);
    }
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async () => {
    if (!description.trim()) return;
    setLoading(true);
    setReport(null);

    const apiUrl = import.meta.env.VITE_API_URL || "";

    try {
      const body = new FormData();
      body.append("prompt", description);
      for (const file of files) {
        body.append("files", file);
      }

      const submitRes = await fetch(`${apiUrl}/api/stack-run`, {
        method: "POST",
        body,
        cache: "no-store",
      });
      const submitData = await submitRes.json();

      if (!submitRes.ok) {
        throw new Error(submitData.error || "Request failed");
      }

      const { jobId } = submitData;

      while (true) {
        await new Promise((r) => setTimeout(r, 3000));

        const pollRes = await fetch(`${apiUrl}/api/status/${jobId}`, {
          cache: "no-store",
        });
        if (pollRes.status === 304) {
          continue;
        }
        if (!pollRes.ok) {
          throw new Error("Status polling failed");
        }
        const job = await pollRes.json();

        if (job.status === "done") {
          setReport(job.output);
          return;
        }

        if (job.status === "error") {
          throw new Error(job.error || "Processing failed");
        }
      }
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Unexpected error.";
      toast({ title: "Request failed", description: message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border px-6 py-4">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <span className="text-3xl font-bold tracking-tight text-foreground">
            Op-Σra
          </span>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-12">
        {/* Hero */}
        <div className="mb-12">
          <p className="mb-2 text-xs uppercase tracking-[0.2em] text-primary">
            Formulation Engine
          </p>
          <h1 className="mb-3 font-sans text-4xl font-bold tracking-tight text-foreground md:text-5xl">
            Describe Your Problem.
          </h1>
          <p className="max-w-xl text-sm leading-relaxed text-muted-foreground">
            Provide a natural-language description of your optimization problem
            and any supporting files. Our AI will generate a consultant-grade
            report.
          </p>
        </div>

        {/* Input Panel */}
        <div className="mb-8 rounded border border-border bg-card">
          {/* Top bar */}
          <div className="flex items-center justify-between border-b border-border px-4 py-2">
            <span className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
              Input
            </span>
            <span className="flex h-2 w-2 rounded-full bg-primary" />
          </div>

          {/* Description */}
          <div className="border-b border-border p-4">
            <label className="mb-2 block text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
              Problem Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={`"Minimize total delivery cost across all vehicles while ensuring every customer is visited exactly once, each vehicle starts and ends at the depot, no vehicle exceeds its capacity, and all deliveries arrive within their time windows."`}
              rows={5}
              className="w-full resize-none bg-transparent text-sm leading-relaxed text-foreground placeholder:text-muted-foreground/50 focus:outline-none"
            />
          </div>

          {/* File upload */}
          <div className="p-4">
            <label className="mb-3 block text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
              Supporting Files
            </label>

            {files.length > 0 && (
              <div className="mb-3 flex flex-wrap gap-2">
                {files.map((file, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-2 rounded border border-border bg-muted px-3 py-1.5 text-xs text-foreground"
                  >
                    <FileText className="h-3 w-3 text-muted-foreground" />
                    <span className="max-w-[140px] truncate">{file.name}</span>
                    <button
                      onClick={() => removeFile(i)}
                      className="text-muted-foreground transition-colors hover:text-foreground"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <button
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center gap-2 rounded border border-dashed border-border px-4 py-2 text-xs text-muted-foreground transition-colors hover:border-primary hover:text-primary"
            >
              <Upload className="h-3.5 w-3.5" />
              Upload files
            </button>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              onChange={handleFileChange}
              className="hidden"
            />
          </div>
        </div>

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={!description.trim() || loading}
          className="mb-12 flex items-center gap-2 rounded bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-40"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
          {loading ? "Generating Report..." : "Generate Report"}
        </button>

        {/* Math Animation */}
        {loading && <MathAnimation />}

      </main>

      {/* Report Output — full width for readability */}
      {report && (
        <div ref={reportRef} className="border-t border-border">
          <div className="flex items-center justify-between border-b border-border px-8 py-3">
            <span className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
              Output — Consultant Report
            </span>
            <span className="flex h-2 w-2 rounded-full bg-primary" />
          </div>
          <div className="mx-auto max-w-5xl px-8 py-10">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                // Headings
                h1: ({ ...props }) => (
                  <h1 className="mb-6 mt-2 font-sans text-3xl font-bold tracking-tight text-foreground" {...props} />
                ),
                h2: ({ ...props }) => (
                  <h2 className="mb-4 mt-10 border-b border-border pb-2 font-sans text-xl font-semibold tracking-tight text-foreground" {...props} />
                ),
                h3: ({ ...props }) => (
                  <h3 className="mb-3 mt-7 font-sans text-base font-semibold text-foreground" {...props} />
                ),
                // Paragraphs & lists
                p: ({ ...props }) => (
                  <p className="mb-4 leading-7 text-muted-foreground" {...props} />
                ),
                ul: ({ ...props }) => (
                  <ul className="mb-4 ml-6 list-disc space-y-1 text-muted-foreground" {...props} />
                ),
                ol: ({ ...props }) => (
                  <ol className="mb-4 ml-6 list-decimal space-y-1 text-muted-foreground" {...props} />
                ),
                li: ({ ...props }) => (
                  <li className="leading-7" {...props} />
                ),
                strong: ({ ...props }) => (
                  <strong className="font-semibold text-foreground" {...props} />
                ),
                // Tables
                table: ({ ...props }) => (
                  <div className="my-6 overflow-x-auto rounded border border-border">
                    <table className="min-w-full text-sm" {...props} />
                  </div>
                ),
                thead: ({ ...props }) => (
                  <thead className="bg-muted/60" {...props} />
                ),
                th: ({ ...props }) => (
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-foreground" {...props} />
                ),
                td: ({ ...props }) => (
                  <td className="border-t border-border px-4 py-3 align-top text-muted-foreground" {...props} />
                ),
                tr: ({ ...props }) => (
                  <tr className="transition-colors hover:bg-muted/20" {...props} />
                ),
                // Code blocks — mermaid diagrams or plain code
                code: ({ className, children, ...props }) => {
                  const language = /language-(\w+)/.exec(className || "")?.[1];
                  const code = String(children).trim();
                  if (language === "mermaid") {
                    return (
                      <Suspense fallback={<div className="h-32 animate-pulse rounded border border-border bg-muted" />}>
                        <MermaidChart code={code} />
                      </Suspense>
                    );
                  }
                  return (
                    <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs text-primary" {...props}>
                      {children}
                    </code>
                  );
                },
                pre: ({ children, ...props }) => (
                  <pre className="my-4 overflow-x-auto rounded border border-border bg-muted p-4 font-mono text-xs text-muted-foreground" {...props}>
                    {children}
                  </pre>
                ),
                // Horizontal rule
                hr: () => <hr className="my-8 border-border" />,
                // Blockquote
                blockquote: ({ ...props }) => (
                  <blockquote className="my-4 border-l-2 border-primary pl-4 italic text-muted-foreground" {...props} />
                ),
              }}
            >
              {report}
            </ReactMarkdown>
          </div>
        </div>
      )}

    </div>
  );
};

export default Index;
