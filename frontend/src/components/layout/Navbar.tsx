import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import nedLogo from "../../assets/LOGONEDUET2LOGO_1.webp";

export function Navbar() {
  const { isAuthenticated, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    setCollapsed(false);
  }, []);

  const isAdminArea = location.pathname.startsWith("/admin");

  function handleLogout() {
    logout();
    navigate("/admin/login");
  }

  return (
    <header className="sticky top-0 z-50 border-b border-slate-200 bg-white shadow-md">
      <div className="mx-auto max-w-7xl px-4">

        {/* Logo */}
{!collapsed && (
  <div className="flex justify-center py-3">
    <img
      src={nedLogo}
      alt="NED University"
      className="h-20 w-auto"
    />
  </div>
)}

        {/* Navigation */}
        <div
          className={`flex items-center justify-center gap-4 transition-all duration-300 ${
            collapsed
              ? "py-2"
              : "border-t border-slate-200 py-3"
          }`}
        >
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