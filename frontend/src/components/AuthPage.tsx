import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AuthMode, AuthResponse } from "../types";

export default function AuthPage({ mode }: { mode: AuthMode }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [username, setUsername] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError("");

    const endpoint =
      mode === "login" ? "/api/v1/auth/login" : "/api/v1/auth/register";
    const payload =
      mode === "login" ? { email, password } : { username, email, password };

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        credentials: "include",          // ← receive HttpOnly cookies from server
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const text = await res.text();
      let data: Record<string, unknown> = {};
      try { data = JSON.parse(text); } catch { /**/ }

      if (!res.ok) {
        throw new Error(
          typeof data?.detail === "string" ? data.detail : `error_${res.status}`
        );
      }

      // Tokens live in HttpOnly cookies (set by the server above).
      // We don't touch localStorage for security — the readable `username`
      // cookie was also set by the server and is used by the frontend.
      const auth = data as AuthResponse;
      void auth; // used for type-narrowing only; no manual storage needed

      navigate("/app");
    } catch (err) {
      setError(err instanceof Error ? err.message : "request_failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-bg flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <Link
            to="/"
            className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-cyan-600 transition"
          >
            ← Back to home
          </Link>
        </div>

        <div className="rounded-3xl border border-slate-200/80 bg-white p-8 panel-shadow">
          <div className="mb-6 inline-flex rounded-full bg-slate-100 p-1">
            <Link
              to="/login"
              className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
                mode === "login"
                  ? "bg-slate-900 text-white"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Login
            </Link>
            <Link
              to="/signup"
              className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
                mode === "signup"
                  ? "bg-slate-900 text-white"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Sign Up
            </Link>
          </div>

          <h1
            className="text-2xl font-bold text-slate-900"
            style={{ fontFamily: "'Space Grotesk',sans-serif" }}
          >
            {mode === "login" ? "Welcome back" : "Create your account"}
          </h1>

          <form className="mt-6 space-y-4" onSubmit={onSubmit}>
            {mode === "signup" && (
              <label className="block">
                <span className="mb-1 block text-sm font-medium text-slate-700">
                  Username
                </span>
                <input
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  minLength={3}
                  className="w-full rounded-xl border border-slate-300 px-3 py-2.5 outline-none transition focus:border-cyan-500 focus:ring-2 focus:ring-cyan-200"
                  placeholder="you"
                />
              </label>
            )}

            <label className="block">
              <span className="mb-1 block text-sm font-medium text-slate-700">
                Email
              </span>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full rounded-xl border border-slate-300 px-3 py-2.5 outline-none transition focus:border-cyan-500 focus:ring-2 focus:ring-cyan-200"
                placeholder="you@example.com"
              />
            </label>

            <label className="block">
              <span className="mb-1 block text-sm font-medium text-slate-700">
                Password
              </span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                className="w-full rounded-xl border border-slate-300 px-3 py-2.5 outline-none transition focus:border-cyan-500 focus:ring-2 focus:ring-cyan-200"
                placeholder="••••••••"
              />
            </label>

            {error && (
              <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-60"
            >
              {loading
                ? "Please wait…"
                : mode === "login"
                ? "Sign In"
                : "Create Account"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
