import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, getToken, setToken } from "../lib/api";

// Auth context (build prompt Section 5.5 useAuth). Token persists in
// localStorage; /environments and /dashboard are guarded in App.tsx.
// Deliberately minimal per Section 4.1 — no roles, no reset flow.

interface AuthState {
  token: string | null;
  email: string | null;
  login: (email: string, password: string) => Promise<string | null>;
  signup: (email: string, password: string) => Promise<string | null>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

function emailFromToken(): string | null {
  // the JWT payload's email claim, if present; demo-scale, not security
  try {
    const token = getToken();
    if (!token) return null;
    const payload = JSON.parse(atob(token.split(".")[1]));
    return typeof payload.email === "string" ? payload.email : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTok] = useState<string | null>(getToken());
  const [email, setEmail] = useState<string | null>(() => emailFromToken());

  const login = useCallback(async (e: string, p: string) => {
    const res = await api.login(e, p);
    if (res.ok && res.data && typeof res.data === "object" && "token" in res.data) {
      const data = res.data as { token: string; user: { email: string } };
      setToken(data.token);
      setTok(data.token);
      setEmail(data.user.email);
      return null;
    }
    const detail =
      res.data && typeof res.data === "object" && "detail" in res.data
        ? String((res.data as { detail: unknown }).detail)
        : "login failed";
    return detail;
  }, []);

  const signup = useCallback(async (e: string, p: string) => {
    const res = await api.signup(e, p);
    if (res.ok && res.data && typeof res.data === "object" && "token" in res.data) {
      const data = res.data as { token: string; user: { email: string } };
      setToken(data.token);
      setTok(data.token);
      setEmail(data.user.email);
      return null;
    }
    const detail =
      res.data && typeof res.data === "object" && "detail" in res.data
        ? String((res.data as { detail: unknown }).detail)
        : "sign-up failed";
    return detail;
  }, []);

  const logout = useCallback(() => {
    void api.logout();
    setToken(null);
    setTok(null);
    setEmail(null);
  }, []);

  const value = useMemo(
    () => ({ token, email, login, signup, logout }),
    [token, email, login, signup, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
