import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { login, signup } from "../api/auth";

export default function LoginPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [workspace, setWorkspace] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "login") await login(email, password);
      else await signup(email, password, workspace);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ maxWidth: 360, margin: "10vh auto", fontFamily: "system-ui" }}>
      <h1>SlothOps</h1>
      <form onSubmit={onSubmit} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <input
          type="email"
          placeholder="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input
          type="password"
          placeholder="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {mode === "signup" && (
          <input
            type="text"
            placeholder="workspace name"
            value={workspace}
            onChange={(e) => setWorkspace(e.target.value)}
            required
          />
        )}
        <button type="submit" disabled={busy}>
          {busy ? "..." : mode === "login" ? "Sign in" : "Create workspace"}
        </button>
        <button
          type="button"
          onClick={() => setMode(mode === "login" ? "signup" : "login")}
        >
          {mode === "login" ? "Need an account?" : "Have an account?"}
        </button>
        {error && <div style={{ color: "tomato" }}>{error}</div>}
      </form>
    </div>
  );
}
