/**
 * lib/auth.tsx — Contexte d'authentification global.
 *
 * Fournit user, token, login/logout à toute l'application.
 * Le token est persisté en localStorage.
 */

"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { getMe, User } from "./api";

interface AuthCtx {
  user:    User | null;
  token:   string | null;
  loading: boolean;
  setToken: (token: string) => void;
  logout:  () => void;
}

const Ctx = createContext<AuthCtx>({
  user: null, token: null, loading: true,
  setToken: () => {}, logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token,   setTokenState] = useState<string | null>(null);
  const [user,    setUser]       = useState<User | null>(null);
  const [loading, setLoading]    = useState(true);

  // Restaure le token depuis localStorage au montage
  useEffect(() => {
    const stored = localStorage.getItem("token");
    if (stored) {
      setTokenState(stored);
      getMe()
        .then(setUser)
        .catch(() => { localStorage.removeItem("token"); setTokenState(null); })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const setToken = (t: string) => {
    localStorage.setItem("token", t);
    setTokenState(t);
    getMe().then(setUser).catch(() => {});
  };

  const logout = () => {
    localStorage.removeItem("token");
    setTokenState(null);
    setUser(null);
  };

  return (
    <Ctx.Provider value={{ user, token, loading, setToken, logout }}>
      {children}
    </Ctx.Provider>
  );
}

export const useAuth = () => useContext(Ctx);
