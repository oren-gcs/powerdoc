import React, { createContext, useContext, useEffect, useState } from "react";
import { AuthAPI, clearTokens, getToken, setTokens } from "./api";

type User = {
  id: number;
  email: string;
  full_name: string;
  role: string;
  tenant_id: number;
  locale?: string;
};

const Ctx = createContext<{
  user: User | null;
  loading: boolean;
  login: (e: string, p: string) => Promise<void>;
  register: (p: any) => Promise<void>;
  logout: () => void;
}>({ user: null, loading: true, login: async () => {}, register: async () => {}, logout: () => {} });

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    AuthAPI.me()
      .then(setUser)
      .catch(() => clearTokens())
      .finally(() => setLoading(false));
  }, []);

  const login = async (email: string, password: string) => {
    const t = await AuthAPI.login(email, password);
    setTokens(t.access_token, t.refresh_token);
    setUser(await AuthAPI.me());
  };
  const register = async (payload: any) => {
    const t = await AuthAPI.register(payload);
    setTokens(t.access_token, t.refresh_token);
    setUser(await AuthAPI.me());
  };
  const logout = () => {
    clearTokens();
    setUser(null);
    window.location.href = "/";
  };

  return <Ctx.Provider value={{ user, loading, login, register, logout }}>{children}</Ctx.Provider>;
}

export function useAuth() {
  return useContext(Ctx);
}
