import { Navigate, Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "../components/ProtectedRoute";
import { RoleProtectedRoute } from "../components/RoleProtectedRoute";
import { useAuth } from "../hooks/useAuth";
import { AppLayout } from "../layouts/AppLayout";
import { AuthLayout } from "../layouts/AuthLayout";
import { AdminAnalyticsPage } from "../pages/admin/AdminAnalyticsPage";
import { AdminDashboardPage } from "../pages/admin/AdminDashboardPage";
import { AdminKnowledgePage } from "../pages/admin/AdminKnowledgePage";
import { AdminUsersPage } from "../pages/admin/AdminUsersPage";
import { AgentDashboardPage } from "../pages/agent/AgentDashboardPage";
import { AgentTicketDetailPage } from "../pages/agent/AgentTicketDetailPage";
import { AgentTicketsPage } from "../pages/agent/AgentTicketsPage";
import { CustomerDashboardPage } from "../pages/customer/CustomerDashboardPage";
import { CustomerTicketDetailPage } from "../pages/customer/CustomerTicketDetailPage";
import { CustomerTicketsPage } from "../pages/customer/CustomerTicketsPage";
import { NewTicketPage } from "../pages/customer/NewTicketPage";
import { LoginPage } from "../pages/LoginPage";
import { NotFoundPage } from "../pages/NotFoundPage";
import { ProfilePage } from "../pages/ProfilePage";
import { RegisterPage } from "../pages/RegisterPage";
import { homePathForRole } from "../utils/roles";

function HomeRedirect() {
  const { user, isLoading } = useAuth();
  if (isLoading) return null;
  return <Navigate to={user ? homePathForRole(user.role) : "/login"} replace />;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<HomeRedirect />} />

      <Route element={<AuthLayout />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/profile" element={<ProfilePage />} />

          <Route element={<RoleProtectedRoute allowedRoles={["CUSTOMER"]} />}>
            <Route path="/customer/dashboard" element={<CustomerDashboardPage />} />
            <Route path="/customer/tickets" element={<CustomerTicketsPage />} />
            <Route path="/customer/tickets/new" element={<NewTicketPage />} />
            <Route path="/customer/tickets/:id" element={<CustomerTicketDetailPage />} />
          </Route>

          <Route element={<RoleProtectedRoute allowedRoles={["AGENT", "ADMIN"]} />}>
            <Route path="/agent/dashboard" element={<AgentDashboardPage />} />
            <Route path="/agent/tickets" element={<AgentTicketsPage />} />
            <Route path="/agent/tickets/:id" element={<AgentTicketDetailPage />} />
          </Route>

          <Route element={<RoleProtectedRoute allowedRoles={["ADMIN"]} />}>
            <Route path="/admin/dashboard" element={<AdminDashboardPage />} />
            <Route path="/admin/users" element={<AdminUsersPage />} />
            <Route path="/admin/knowledge" element={<AdminKnowledgePage />} />
            <Route path="/admin/analytics" element={<AdminAnalyticsPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
