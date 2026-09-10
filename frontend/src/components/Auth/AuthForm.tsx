import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Activity } from "lucide-react";
import { useAuth } from "../../hooks/useAuth";

// Shared shell for the login/signup forms (Section 4.1 — deliberately
// minimal: email + password only, no OAuth/reset/verification).

interface Props {
  mode: "login" | "signup";
}

export function AuthForm({ mode }: Props) {
  const { login, signup } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const err = mode === "login" ? await login(email, password) : await signup(email, password);
    setBusy(false);
    if (err) {
      setError(err);
      return;
    }
    navigate("/environments");
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0B0E14] px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center gap-2">
          <Activity size={20} className="text-[#00E5FF]" />
          <span className="text-lg font-bold tracking-wide text-[#E8ECF4]">ChainBreak</span>
        </div>

        <div className="rounded-xl border border-[#232B3D] bg-[#11151F] p-6">
          <h1 className="mb-1 text-lg font-bold text-[#E8ECF4]">
            {mode === "login" ? "Sign in" : "Create account"}
          </h1>
          <p className="mb-5 text-xs text-[#8A94A8]">
            {mode === "login"
              ? "Welcome back. Enter your credentials."
              : "Email + password only — demo-scale gate, no verification email."}
          </p>

          <form onSubmit={submit} className="space-y-4">
            <div>
              <label htmlFor="email" className="mb-1 block text-[11px] font-semibold text-[#8A94A8]">
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-md border border-[#232B3D] bg-[#0B0E14] px-3 py-2 text-sm text-[#E8ECF4] outline-none transition focus:border-[#00E5FF]/60"
                placeholder="you@example.com"
              />
            </div>
            <div>
              <label htmlFor="password" className="mb-1 block text-[11px] font-semibold text-[#8A94A8]">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                minLength={8}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-md border border-[#232B3D] bg-[#0B0E14] px-3 py-2 text-sm text-[#E8ECF4] outline-none transition focus:border-[#00E5FF]/60"
                placeholder="minimum 8 characters"
              />
            </div>

            {error && (
              <div className="rounded-md border border-[#FF3B3B]/50 bg-[#FF3B3B]/10 px-3 py-2 text-[11px] font-semibold text-[#FF3B3B]">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={busy}
              className="w-full rounded-md border border-[#00E5FF]/50 bg-[#00E5FF]/15 px-4 py-2.5 text-sm font-bold text-[#00E5FF] transition hover:bg-[#00E5FF]/25 disabled:opacity-50"
            >
              {busy ? "Working…" : mode === "login" ? "Sign in" : "Create account"}
            </button>
          </form>

          <div className="mt-4 text-center text-[11px] text-[#8A94A8]">
            {mode === "login" ? (
              <>No account? <Link to="/signup" className="text-[#00E5FF] hover:underline">Sign up</Link></>
            ) : (
              <>Already registered? <Link to="/login" className="text-[#00E5FF] hover:underline">Sign in</Link></>
            )}
          </div>
        </div>

        <div className="mt-4 text-center">
          <Link to="/" className="text-[11px] text-[#5A6472] hover:text-[#8A94A8]">
            ← Back to briefing
          </Link>
        </div>
      </div>
    </div>
  );
}
