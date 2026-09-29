import type { ReactNode } from "react";
import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import type { UserRole } from "../types";
import { homePathForRole } from "../utils/roles";

interface RoleProtectedRouteProps {
  allowedRoles: UserRole[];
  children?: ReactNode;
}

/** Must be nested inside ProtectedRoute. Redirects users without an allowed role to their home page. */
export function RoleProtectedRoute({ allowedRoles, children }: RoleProtectedRouteProps) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (!allowedRoles.includes(user.role)) {
    return <Navigate to={homePathForRole(user.role)} replace />;
  }
  return children ? <>{children}</> : <Outlet />;
}
