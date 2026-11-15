import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, getToken, setToken, setUnauthorizedHandler } from "./api";

const AuthCtx = createContext(null);
export const useAuth = () => useContext(AuthCtx);

export const ROLE_LABELS = {
  superadmin: "Superadministrador", company_admin: "Administrador de empresa", manager: "Gerente",
  supervisor: "Supervisor", operator: "Operador", warehouse: "Encargado de almacén",
};

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  const logout = useCallback(() => { setToken(null); setUser(null); }, []);
  useEffect(() => { setUnauthorizedHandler(logout); }, [logout]);

  useEffect(() => {
    if (!getToken()) return setReady(true);
    api("/auth/me").then(setUser).catch(() => setToken(null)).finally(() => setReady(true));
  }, []);

  const startSession = (data) => { setToken(data.access_token); setUser(data.user); };
  const login = async (email, password) => startSession(await api("/auth/login", { method: "POST", body: { email, password } }));
  const register = async (body) => startSession(await api("/auth/register-company", { method: "POST", body }));
  const signOut = async () => { try { await api("/auth/logout", { method: "POST" }); } catch {} logout(); };

  return <AuthCtx.Provider value={{ user, ready, login, register, signOut }}>{children}</AuthCtx.Provider>;
}
