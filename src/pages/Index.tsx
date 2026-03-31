import { useState, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { Upload, X, Send, FileText, Loader2 } from "lucide-react";
import { toast } from "@/hooks/use-toast";

const Index = () => {
  const [description, setDescription] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [report, setReport] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
      });
      const submitData = await submitRes.json();

      if (!submitRes.ok) {
        throw new Error(submitData.error || "Request failed");
      }

      const { jobId } = submitData;

      while (true) {
        await new Promise((r) => setTimeout(r, 3000));

        const pollRes = await fetch(`${apiUrl}/api/status/${jobId}`);
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
          <span className="text-lg font-semibold tracking-tight text-foreground">
            Op-Σra
          </span>
          <span className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
            AI Optimization Consulting
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

        {/* Report Output */}
        {report && (
          <div className="rounded border border-border bg-card">
            <div className="flex items-center justify-between border-b border-border px-4 py-2">
              <span className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
                Output — Consultant Report
              </span>
              <span className="flex h-2 w-2 rounded-full bg-primary" />
            </div>
            <div className="prose prose-invert prose-sm max-w-none p-6 prose-headings:font-sans prose-headings:tracking-tight prose-h1:text-2xl prose-h2:text-lg prose-h3:text-base prose-p:text-muted-foreground prose-strong:text-foreground prose-td:text-muted-foreground prose-th:text-foreground">
              <ReactMarkdown>{report}</ReactMarkdown>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default Index;
