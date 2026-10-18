import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import nedLogo from "../../assets/LOGONEDUET2LOGO_1.webp";

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
    <header className="sticky top-0 z-50 border-b border-slate-200 bg-white shadow-md">
      <div className="relative flex h-20 w-full items-center px-6">
        {/* NED Logo */}
        <Link
          to="/chat"
          className="flex items-center"
        >
          <img
            src={nedLogo}
            alt="NED University"
            className="h-21 w-auto"
          />
        </Link>

        {/* Navigation */}
        <div className="absolute left-1/2 flex -translate-x-1/2 items-center gap-4">
          <Link
            to="/chat"
            className={`rounded-full px-5 py-2 font-medium transition ${
              !isAdminArea
                ? "bg-[#163A6B] text-white"
                : "text-slate-700 hover:bg-slate-100"
            }`}
          >
            Chat
          </Link>

          {isAuthenticated ? (
            <>
              <Link
                to="/admin"
                className={`rounded-full px-5 py-2 font-medium transition ${
                  isAdminArea
                    ? "bg-[#7A1533] text-white"
                    : "text-slate-700 hover:bg-slate-100"
                }`}
              >
                Dashboard
              </Link>

              <button
                onClick={handleLogout}
                className="rounded-full bg-red-600 px-5 py-2 text-white transition hover:bg-red-700"
              >
                Logout
              </button>
            </>
          ) : (
            <Link
              to="/admin/login"
              className={`rounded-full px-5 py-2 font-medium transition ${
                isAdminArea
                  ? "bg-[#7A1533] text-white"
                  : "text-slate-700 hover:bg-slate-100"
              }`}
            >
              Admin
            </Link>
          )}
        </div>

      </div>
    </header>
  );
}