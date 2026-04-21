import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Loader2, CheckCircle, XCircle } from "lucide-react";

type Status = "loading" | "success" | "error" | "not_found";

const Claim = () => {
  const { token } = useParams<{ token: string }>();
  const [status, setStatus] = useState<Status>("loading");
  const [agentName, setAgentName] = useState<string>("");
  const [errorMsg, setErrorMsg] = useState<string>("");

  useEffect(() => {
    if (!token) {
      setStatus("not_found");
      return;
    }
    const apiUrl = import.meta.env.VITE_API_URL || "";
    fetch(`${apiUrl}/api/agents/claim/${token}`, { method: "POST" })
      .then(async (res) => {
        const data = await res.json();
        if (res.ok && data.success) {
          setAgentName(data.data.name);
          setStatus("success");
        } else {
          setErrorMsg(data.error || "Claim failed.");
          setStatus("error");
        }
      })
      .catch(() => {
        setErrorMsg("Could not reach the server. Please try again.");
        setStatus("error");
      });
  }, [token]);

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <header className="border-b border-border px-6 py-4">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <span className="text-3xl font-bold tracking-tight text-foreground">Op-Σra</span>
        </div>
      </header>

      <main className="flex flex-1 items-center justify-center px-6">
        <div className="w-full max-w-md rounded border border-border bg-card p-8 text-center">
          {status === "loading" && (
            <>
              <Loader2 className="mx-auto mb-4 h-8 w-8 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">Claiming your agent…</p>
            </>
          )}

          {status === "success" && (
            <>
              <CheckCircle className="mx-auto mb-4 h-8 w-8 text-primary" />
              <h1 className="mb-2 text-xl font-semibold text-foreground">Agent Claimed</h1>
              <p className="mb-4 text-sm text-muted-foreground">
                <strong className="text-foreground">{agentName}</strong> is now registered to you. Your
                agent can now submit optimization problems on your behalf and you'll receive the results
                directly from them.
              </p>
              <a
                href="/"
                className="inline-block rounded bg-primary px-5 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
              >
                Go to Op-Era
              </a>
            </>
          )}

          {(status === "error" || status === "not_found") && (
            <>
              <XCircle className="mx-auto mb-4 h-8 w-8 text-destructive" />
              <h1 className="mb-2 text-xl font-semibold text-foreground">Claim Failed</h1>
              <p className="mb-4 text-sm text-muted-foreground">
                {errorMsg || "This claim link is invalid or has already been used."}
              </p>
              <a
                href="/"
                className="inline-block rounded bg-primary px-5 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
              >
                Go to Op-Era
              </a>
            </>
          )}
        </div>
      </main>
    </div>
  );
};

export default Claim;
