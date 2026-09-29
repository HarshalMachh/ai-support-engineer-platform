import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { homePathForRole } from "../utils/roles";

export function AuthLayout() {
  const { user, isLoading } = useAuth();
  if (!isLoading && user) {
    return <Navigate to={homePathForRole(user.role)} replace />;
  }
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-b from-slate-50 to-slate-100 px-4">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-brand-600 font-mono text-sm font-bold text-white">
            AI
          </span>
          <h1 className="mt-3 text-lg font-semibold text-slate-900">AI Support Engineer Platform</h1>
          <p className="text-sm text-slate-500">Customer support with a human-reviewed AI assistant</p>
        </div>
        <Outlet />
      </div>
    </div>
  );
}
