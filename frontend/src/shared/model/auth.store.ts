import { create } from "zustand";
import { api, ApiError } from "@/shared/api/client";
import { tokens } from "@/shared/api/tokens";
import { wsClient } from "@/shared/api/ws";

export type Permission = { resource: string; action: string; scope: string };
export type Me = {
  id: string;
  full_name: string;
  phone: string;
  is_owner: boolean;
  owner_type: string | null;
  roles: string[];
  permissions: Permission[];
  businesses: string[];
};

type AuthState = {
  user: Me | null;
  loading: boolean;
  ready: boolean;
  error: string | null;
  login: (phone: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  loadMe: () => Promise<void>;
  can: (resource: string, action: string) => boolean;
};

export const useAuth = create<AuthState>((set, get) => ({
  user: null,
  loading: false,
  ready: false,
  error: null,

  login: async (phone, password) => {
    set({ loading: true, error: null });
    try {
      const t = await api.post("/api/auth/login", { phone, password }, false);
      tokens.setAccess(t.access_token); // access — только в памяти; refresh ушёл в httpOnly cookie
      await get().loadMe();
      wsClient.connect();
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Ошибка входа";
      set({ error: msg, loading: false });
      throw e;
    }
  },

  // На старте access-токена в памяти нет — клиент тихо восстановит его через refresh-cookie (в api.get).
  loadMe: async () => {
    try {
      const me = await api.get<Me>("/api/auth/me");
      set({ user: me, loading: false, ready: true });
      wsClient.connect();
    } catch {
      tokens.clear();
      set({ user: null, loading: false, ready: true });
    }
  },

  logout: async () => {
    try {
      await api.post("/api/auth/logout", undefined, false); // сервер чистит refresh-cookie
    } catch {
      /* игнор */
    }
    tokens.clear();
    wsClient.close();
    // чистим кешированные данные, чтобы после выхода ничего не оставалось
    try {
      const { queryClient } = await import("@/shared/api/query");
      queryClient.clear();
    } catch {
      /* игнор */
    }
    try {
      sessionStorage.removeItem("arkand-query-cache");
    } catch {
      /* игнор */
    }
    set({ user: null });
  },

  // UI-gating прав (зеркало бэкенда, §14 — реальная защита на бэке)
  can: (resource, action) => {
    const u = get().user;
    if (!u) return false;
    if (u.is_owner && (u.owner_type === "sohib" || u.owner_type === "iftikhor")) return true;
    return u.permissions.some(
      (p) => (p.resource === resource || p.resource === "*") && (p.action === action || p.action === "*"),
    );
  },
}));
