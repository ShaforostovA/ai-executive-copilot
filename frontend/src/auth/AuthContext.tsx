import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { ApiError, api } from "../lib/api";
import type { LoginCredentials, Principal } from "../types";

interface AuthContextValue {
  user: Principal | null;
  loading: boolean;
  error: string | null;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
  expireSession: () => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Principal | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    api
      .me()
      .then((principal) => {
        if (active) setUser(principal);
      })
      .catch((reason: unknown) => {
        if (active && !(reason instanceof ApiError && reason.status === 401)) {
          setError("Не удалось проверить серверную сессию.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(async (credentials: LoginCredentials) => {
    setError(null);
    try {
      setUser(await api.login(credentials));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Ошибка авторизации.");
      throw reason;
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      setError(null);
    } finally {
      setUser(null);
    }
  }, []);

  const expireSession = useCallback(() => setUser(null), []);
  const value = useMemo(
    () => ({ user, loading, error, login, logout, expireSession }),
    [user, loading, error, login, logout, expireSession],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }
  return context;
}
