import type { TokenResponse, User } from "../types";
import { apiClient } from "./client";

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload extends LoginPayload {
  name: string;
}

export const authApi = {
  login: (payload: LoginPayload) => apiClient.post<TokenResponse>("/auth/login", payload).then((r) => r.data),
  register: (payload: RegisterPayload) =>
    apiClient.post<TokenResponse>("/auth/register", payload).then((r) => r.data),
  me: () => apiClient.get<User>("/auth/me").then((r) => r.data),
};
