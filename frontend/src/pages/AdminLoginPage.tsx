import { useState, type FormEvent } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function AdminLoginPage() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (isAuthenticated) {
    navigate("/admin", { replace: true });
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const success = login(username.trim(), password);
    if (success) {
      const state = location.state as { from?: { pathname?: string } } | null;
      const redirectTo = state?.from?.pathname || "/admin";
      navigate(redirectTo, { replace: true });
    } else {
      setError("Incorrect username or password.");
    }
  }

  return (
    <div className="mx-auto flex min-h-[calc(100vh-64px)] max-w-md flex-col justify-center px-4 py-10 sm:px-6">
      <div className="rounded-2xl border border-white bg-white/90 p-8 shadow-card">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-brand-gradient text-xl shadow-soft">
            🔐
          </div>
          <h1 className="font-display text-xl font-semibold text-slate-800">
            Admin sign in
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Manage prospectus documents and processing
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="username"
              className="mb-1 block text-sm font-medium text-slate-600"
            >
              Username
            </label>
            <input
              id="username"
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm text-slate-700 focus:border-brand-blue focus:outline-none focus:ring-2 focus:ring-brand-blue/20"
              placeholder="admin"
              required
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="mb-1 block text-sm font-medium text-slate-600"
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm text-slate-700 focus:border-brand-blue focus:outline-none focus:ring-2 focus:ring-brand-blue/20"
              placeholder="••••••••"
              required
            />
          </div>

          {error && (
            <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-600">
              {error}
            </p>
          )}

          <button
            type="submit"
            className="w-full rounded-xl bg-brand-gradient px-4 py-2.5 text-sm font-semibold text-white shadow-soft transition-opacity hover:opacity-90"
          >
            Sign in
          </button>
        </form>

        <div className="mt-5 rounded-xl bg-amber-50 px-3.5 py-3 text-xs text-amber-800">
          <p className="font-semibold">Development-only mock login</p>
          <p className="mt-1">
            The real admin backend isn't connected yet. Use{" "}
            <code className="rounded bg-amber-100 px-1 py-0.5">admin</code> /{" "}
            <code className="rounded bg-amber-100 px-1 py-0.5">
              prospectus-dev-only
            </code>{" "}
            to preview the dashboard locally. This session lives only in your
            browser tab and is never sent to any server.
          </p>
        </div>
      </div>
    </div>
  );
}
