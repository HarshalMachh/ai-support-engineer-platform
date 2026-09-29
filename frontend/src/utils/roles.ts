import type { UserRole } from "../types";

export function homePathForRole(role: UserRole): string {
  switch (role) {
    case "ADMIN":
      return "/admin/dashboard";
    case "AGENT":
      return "/agent/dashboard";
    default:
      return "/customer/dashboard";
  }
}

export function ticketPathForRole(role: UserRole, ticketId: number): string {
  return role === "CUSTOMER" ? `/customer/tickets/${ticketId}` : `/agent/tickets/${ticketId}`;
}

export const isStaffRole = (role: UserRole | undefined): boolean => role === "AGENT" || role === "ADMIN";
