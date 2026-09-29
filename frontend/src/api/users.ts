import type { Page, User, UserBrief, UserRole } from "../types";
import { apiClient } from "./client";

export interface UserListParams {
  role?: UserRole | "";
  search?: string;
  page?: number;
  page_size?: number;
}

export const usersApi = {
  list: (params: UserListParams) =>
    apiClient
      .get<Page<User>>("/users", {
        params: Object.fromEntries(Object.entries(params).filter(([, v]) => v !== "" && v !== undefined)),
      })
      .then((r) => r.data),
  agents: () => apiClient.get<UserBrief[]>("/users/agents").then((r) => r.data),
};
