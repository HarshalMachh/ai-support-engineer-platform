import axios, { AxiosError } from "axios";
import { tokenStorage } from "../utils/tokenStorage";

export const API_URL = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export const apiClient = axios.create({
  baseURL: `${API_URL}/api`,
  timeout: 30_000,
});

apiClient.interceptors.request.use((config) => {
  const token = tokenStorage.get();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

type UnauthorizedHandler = () => void;
let onUnauthorized: UnauthorizedHandler | null = null;

/** The AuthProvider registers a handler that logs the user out on 401 responses. */
export function setUnauthorizedHandler(handler: UnauthorizedHandler | null): void {
  onUnauthorized = handler;
}

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const isLoginRequest = error.config?.url?.includes("/auth/login");
    if (error.response?.status === 401 && !isLoginRequest && tokenStorage.get()) {
      tokenStorage.clear();
      onUnauthorized?.();
    }
    return Promise.reject(error);
  },
);

export function websocketUrl(path: string): string {
  const base = API_URL.replace(/^http/, "ws");
  return `${base}/api${path}`;
}
