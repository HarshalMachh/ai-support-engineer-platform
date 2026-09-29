import { NavLink } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import type { UserRole } from "../types";

interface NavItem {
  to: string;
  label: string;
}

const NAV_ITEMS: Record<UserRole, NavItem[]> = {
  CUSTOMER: [
    { to: "/customer/dashboard", label: "Dashboard" },
    { to: "/customer/tickets", label: "My tickets" },
    { to: "/customer/tickets/new", label: "New ticket" },
    { to: "/profile", label: "Profile" },
  ],
  AGENT: [
    { to: "/agent/dashboard", label: "Dashboard" },
    { to: "/agent/tickets", label: "Ticket queue" },
    { to: "/profile", label: "Profile" },
  ],
  ADMIN: [
    { to: "/admin/dashboard", label: "Dashboard" },
    { to: "/agent/tickets", label: "Ticket queue" },
    { to: "/admin/users", label: "Users" },
    { to: "/admin/knowledge", label: "Knowledge base" },
    { to: "/admin/analytics", label: "Analytics" },
    { to: "/profile", label: "Profile" },
  ],
};

export function Sidebar() {
  const { user } = useAuth();
  if (!user) return null;

  return (
    <aside className="hidden w-56 shrink-0 border-r border-slate-200 bg-white md:block">
      <nav className="space-y-1 p-3" aria-label="Main navigation">
        {NAV_ITEMS[user.role].map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end
            className={({ isActive }) =>
              `block rounded-md px-3 py-2 text-sm font-medium ${
                isActive ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
              }`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
