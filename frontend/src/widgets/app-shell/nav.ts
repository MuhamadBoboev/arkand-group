import type { IconType } from "react-icons";
import {
  LuLayoutDashboard,
  LuWallet,
  LuReceipt,
  LuPackage,
  LuBuilding2,
  LuPencilRuler,
  LuFactory,
  LuMountain,
  LuShieldCheck,
  LuClipboardCheck,
} from "react-icons/lu";
import type { useAuth } from "@/shared/model/auth.store";

type Auth = ReturnType<typeof useAuth.getState>;

export interface NavItem {
  to: string;
  label: string;
  icon: IconType;
  show: (a: Auth) => boolean;
}

// Пункты навигации фильтруются по правам пользователя (недоступное скрыто).
export const NAV: NavItem[] = [
  { to: "/", label: "Дашборд", icon: LuLayoutDashboard, show: () => true },
  { to: "/finance", label: "Финансы", icon: LuWallet, show: (a) => a.can("cash", "view") },
  { to: "/inkassaciya", label: "Инкассация", icon: LuReceipt, show: (a) => a.can("inkassaciya", "view") },
  { to: "/supply", label: "Снабжение", icon: LuPackage, show: (a) => a.can("supply_request", "view") || a.can("purchase", "view") },
  { to: "/zastroyshchik", label: "Застройщик", icon: LuBuilding2, show: (a) => a.can("object", "view") },
  { to: "/proektnaya", label: "Проектная", icon: LuPencilRuler, show: (a) => a.can("project", "view") },
  { to: "/beton", label: "Бетон", icon: LuFactory, show: (a) => a.can("order", "view") || a.can("recipe", "view") },
  { to: "/shcheben", label: "Щебень", icon: LuMountain, show: (a) => a.can("fraction", "view") || a.can("order", "view") },
  { to: "/owners", label: "Владельцы", icon: LuShieldCheck, show: (a) => !!a.user?.is_owner || a.can("approval", "approve") || a.can("employee", "view") },
  { to: "/audit", label: "Проверка", icon: LuClipboardCheck, show: (a) => a.can("audit", "view") },
];
