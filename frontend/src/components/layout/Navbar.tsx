import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

export function Navbar() {
  const { isAuthenticated, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const isAdminArea = location.pathname.startsWith("/admin");

  function handleLogout() {
    logout();
    navigate("/admin/login");
  }

  return (
    <header className="sticky top-0 z-20 border-b border-white/60 bg-white/70 backdrop-blur-md">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3 sm:px-6">
        <Link to="/" className="flex items-center gap-2 group">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-brand-gradient shadow-soft text-white font-display font-bold text-sm">
            PA
          </span>
          <span className="font-display text-lg font-semibold text-slate-800 group-hover:text-brand-blue transition-colors">
            ProspectusAI
          </span>
        </Link>

        <nav className="flex items-center gap-2 text-sm font-medium">
          <Link
            to="/chat"
            className={`rounded-full px-3 py-1.5 transition-colors ${
              !isAdminArea
                ? "bg-brand-blue/10 text-brand-blue"
                : "text-slate-500 hover:text-brand-blue"
            }`}
          >
            Chat
          </Link>

          {isAuthenticated ? (
            <>
              <Link
                to="/admin"
                className={`rounded-full px-3 py-1.5 transition-colors ${
                  isAdminArea
                    ? "bg-brand-purple/10 text-brand-purple"
                    : "text-slate-500 hover:text-brand-purple"
                }`}
              >
                Dashboard
              </Link>
              <button
                onClick={handleLogout}
                className="rounded-full px-3 py-1.5 text-slate-500 hover:text-rose-500 transition-colors"
              >
                Log out
              </button>
            </>
          ) : (
            <Link
              to="/admin/login"
              className={`rounded-full px-3 py-1.5 transition-colors ${
                isAdminArea
                  ? "bg-brand-purple/10 text-brand-purple"
                  : "text-slate-500 hover:text-brand-purple"
              }`}
            >
              Admin
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
