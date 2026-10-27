import { useEffect, useState, type ReactNode } from "react";
import { ArrowUpRight, LockKeyhole, ShieldCheck } from "lucide-react";
export default function SessionGate({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<{
    required: boolean;
    authenticated: boolean;
    password_login: boolean;
  } | null>(null);
  const [password, setPassword] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function check() {
    try {
      const r = await fetch("/api/session");
      if (!r.ok)
        throw Error(
          "The PRAXIS backend is unavailable. Check the backend service and API proxy configuration.",
        );
      setStatus(await r.json());
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  useEffect(() => {
    check();
  }, []);
  if (status?.authenticated) return children;
  return (
    <main className="session-gate">
      <section>
        <div className="eyebrow">
          <ShieldCheck size={15} /> PRAXIS / PRIVATE DEMO
        </div>
        <LockKeyhole size={36} />
        <h1>
          {status ? "Intelligence. By invitation." : "Connecting to PRAXIS."}
        </h1>
        <p>
          {status?.password_login
            ? "Enter the demo password to access the mission workspace. Inference credentials stay on the server."
            : status
              ? "Browser login is not configured. Set PRAXIS_DEMO_PASSWORD on the backend; API bearer credentials are not requested in the browser."
              : "Checking the backend session and workspace availability."}
        </p>
        {status?.password_login && (
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              setBusy(true);
              setError("");
              try {
                const r = await fetch("/api/session", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ password }),
                });
                const d = await r.json();
                if (!r.ok) throw Error(d.detail || "Login failed");
                setPassword("");
                await check();
              } catch (e) {
                setError((e as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            <label htmlFor="demo-password">Demo password</label>
            <input
              id="demo-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              maxLength={300}
            />
            <button className="primary" disabled={busy}>
              Enter workspace <ArrowUpRight size={16} />
            </button>
          </form>
        )}
        {error && (
          <p className="failure-text" role="alert">
            {error}
          </p>
        )}
        {!status && error && (
          <button className="secondary" onClick={check}>
            Retry connection
          </button>
        )}
        <small>
          HttpOnly session · Same-origin API · Server-side execution
        </small>
      </section>
    </main>
  );
}
