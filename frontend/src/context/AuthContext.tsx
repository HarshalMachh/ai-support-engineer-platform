import { createContext, useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { authApi, type LoginPayload, type RegisterPayload } from "../api/auth";
import { setUnauthorizedHandler } from "../api/client";
import type { User } from "../types";
import { tokenStorage } from "../utils/tokenStorage";

export interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  sessionExpired: boolean;
  login: (payload: LoginPayload) => Promise<User>;
  register: (payload: RegisterPayload) => Promise<User>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(() => Boolean(tokenStorage.get()));
  const [sessionExpired, setSessionExpired] = useState(false);

  const logout = useCallback(() => {
    tokenStorage.clear();
    setUser(null);
    queryClient.clear();
  }, [queryClient]);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setSessionExpired(true);
      setUser(null);
      queryClient.clear();
    });
    return () => setUnauthorizedHandler(null);
  }, [queryClient]);

  useEffect(() => {
    if (!tokenStorage.get()) return;
    let cancelled = false;
    authApi
      .me()
      .then((me) => !cancelled && setUser(me))
      .catch(() => {
        if (!cancelled) tokenStorage.clear();
      })
      .finally(() => !cancelled && setIsLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (payload: LoginPayload) => {
    const response = await authApi.login(payload);
    tokenStorage.set(response.access_token);
    setSessionExpired(false);
    setUser(response.user);
    return response.user;
  }, []);

  const register = useCallback(async (payload: RegisterPayload) => {
    const response = await authApi.register(payload);
    tokenStorage.set(response.access_token);
    setSessionExpired(false);
    setUser(response.user);
    return response.user;
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ user, isLoading, isAuthenticated: Boolean(user), sessionExpired, login, register, logout }),
    [user, isLoading, sessionExpired, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
