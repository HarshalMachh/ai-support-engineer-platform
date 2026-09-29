import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { homePathForRole } from "../utils/roles";
import { humanize } from "../utils/format";

export function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur">
      <div className="flex h-14 items-center justify-between px-4">
        <Link to={user ? homePathForRole(user.role) : "/login"} className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-md bg-brand-600 font-mono text-xs font-bold text-white">
            AI
          </span>
          <span className="text-sm font-semibold text-slate-900">Support Engineer</span>
        </Link>
        {user && (
          <div className="flex items-center gap-3 text-sm">
            <Link to="/profile" className="text-right leading-tight hover:text-brand-700">
              <span className="block font-medium text-slate-800">{user.name}</span>
              <span className="block font-mono text-[11px] text-slate-500">{humanize(user.role)}</span>
            </Link>
            <button type="button" className="btn-secondary py-1" onClick={handleLogout}>
              Log out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
