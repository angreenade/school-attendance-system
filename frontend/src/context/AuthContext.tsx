import { createContext, useContext, useState, type ReactNode } from "react";
import { api } from "../api/client";

interface AuthUser {
  full_name: string;
  role: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => {
    const stored = localStorage.getItem("attendance_user");
    return stored ? JSON.parse(stored) : null;
  });

  async function login(username: string, password: string) {
    const res = await api.post("/api/auth/login", { username, password });
    const { access_token, full_name, role } = res.data;
    localStorage.setItem("attendance_token", access_token);
    const u = { full_name, role };
    localStorage.setItem("attendance_user", JSON.stringify(u));
    setUser(u);
  }

  function logout() {
    localStorage.removeItem("attendance_token");
    localStorage.removeItem("attendance_user");
    setUser(null);
  }

  return <AuthContext.Provider value={{ user, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
