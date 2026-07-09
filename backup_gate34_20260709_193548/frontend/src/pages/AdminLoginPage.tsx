import {
  useEffect,
  useState,
  type FormEvent,
} from "react";
import {
  useLocation,
  useNavigate,
} from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function AdminLoginPage() {
  const {
    login,
    isAuthenticated,
  } = useAuth();

  const navigate = useNavigate();
  const location = useLocation();

  const [username, setUsername] =
    useState("");
  const [password, setPassword] =
    useState("");
  const [error, setError] =
    useState<string | null>(null);
  const [loading, setLoading] =
    useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      navigate("/admin", {
        replace: true,
      });
    }
  }, [
    isAuthenticated,
    navigate,
  ]);

  async function handleSubmit(
    event: FormEvent,
  ) {
    event.preventDefault();
    setError(null);
    setLoading(true);

    const success = await login(
      username.trim(),
      password,
    );

    setLoading(false);

    if (!success) {
      setError(
        "Incorrect username or password.",
      );
      return;
    }

    const state = location.state as {
      from?: {
        pathname?: string;
      };
    } | null;

    navigate(
      state?.from?.pathname || "/admin",
      {
        replace: true,
      },
    );
  }

  return (
    <div className="mx-auto flex min-h-[calc(100vh-64px)] max-w-md flex-col justify-center px-4 py-10 sm:px-6">
      <div className="rounded-2xl border border-white bg-white/90 p-8 shadow-card">
        <div className="mb-6 text-center">
          <h1 className="font-display text-xl font-semibold text-slate-800">
            Admin sign in
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Manage prospectus documents and processing
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="space-y-4"
        >
          <div>
            <label
              htmlFor="username"
              className="mb-1 block text-sm font-medium text-slate-600"
            >
              Username
            </label>
            <input
              id="username"
              autoComplete="username"
              value={username}
              onChange={(event) =>
                setUsername(
                  event.target.value,
                )
              }
              className="w-full rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm"
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
              onChange={(event) =>
                setPassword(
                  event.target.value,
                )
              }
              className="w-full rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm"
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
            disabled={loading}
            className="w-full rounded-xl bg-brand-gradient px-4 py-2.5 text-sm font-semibold text-white shadow-soft disabled:opacity-60"
          >
            {loading
              ? "Signing in..."
              : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
