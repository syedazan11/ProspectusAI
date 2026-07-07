import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="mx-auto flex min-h-[calc(100vh-64px)] max-w-md flex-col items-center justify-center px-4 text-center">
      <div className="mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-brand-gradient text-2xl shadow-soft">
        🧭
      </div>
      <h1 className="font-display text-xl font-semibold text-slate-800">
        Page not found
      </h1>
      <p className="mt-1 text-sm text-slate-500">
        The page you're looking for doesn't exist.
      </p>
      <Link
        to="/chat"
        className="mt-5 rounded-xl bg-brand-gradient px-4 py-2.5 text-sm font-semibold text-white shadow-soft"
      >
        Back to chat
      </Link>
    </div>
  );
}
