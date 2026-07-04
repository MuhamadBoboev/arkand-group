import type { useAuth } from "@/shared/model/auth.store";

type Auth = ReturnType<typeof useAuth.getState>;

export interface NavItem {
  to: string;
  label: string;
  icon: string;
  show: (a: Auth) => boolean;
}

// Пункты навигации фильтруются по правам (§8.5 — фронт скрывает недоступное)
export const NAV: NavItem[] = [
  { to: "/", label: "Дашборд", icon: "🏠", show: () => true },
  { to: "/finance", label: "Финансы", icon: "💰", show: (a) => a.can("cash", "view") },
  { to: "/inkassaciya", label: "Инкассация", icon: "🧾", show: (a) => a.can("inkassaciya", "view") },
  { to: "/supply", label: "Снабжение", icon: "📦", show: (a) => a.can("supply_request", "view") || a.can("purchase", "view") },
  { to: "/zastroyshchik", label: "Застройщик", icon: "🏗️", show: (a) => a.can("object", "view") },
  { to: "/proektnaya", label: "Проектная", icon: "📐", show: (a) => a.can("project", "view") },
  { to: "/beton", label: "Бетон", icon: "🧱", show: (a) => a.can("order", "view") || a.can("recipe", "view") },
  { to: "/shcheben", label: "Щебень", icon: "⛰️", show: (a) => a.can("fraction", "view") || a.can("order", "view") },
  { to: "/owners", label: "Владельцы", icon: "👑", show: (a) => !!a.user?.is_owner || a.can("approval", "approve") || a.can("employee", "view") },
  { to: "/audit", label: "Проверка", icon: "🔍", show: (a) => a.can("audit", "view") },
];
