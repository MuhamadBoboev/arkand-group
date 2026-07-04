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
  logout: () => void;
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
      tokens.set(t.access_token, t.refresh_token);
      await get().loadMe();
      wsClient.connect();
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Ошибка входа";
      set({ error: msg, loading: false });
      throw e;
    }
  },

  loadMe: async () => {
    if (!tokens.access()) {
      set({ user: null, ready: true });
      return;
    }
    try {
      const me = await api.get<Me>("/api/auth/me");
      set({ user: me, loading: false, ready: true });
      wsClient.connect();
    } catch {
      tokens.clear();
      set({ user: null, loading: false, ready: true });
    }
  },

  logout: () => {
    tokens.clear();
    wsClient.close();
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
