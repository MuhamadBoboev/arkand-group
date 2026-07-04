import { Suspense, lazy, useMemo, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { useAuth } from "@/shared/model/auth.store";
import { api } from "@/shared/api/client";
import { queryClient } from "@/shared/api/query";
import { cn } from "@/shared/lib/cn";
import { TableSkeleton } from "@/shared/ui";
import { NAV } from "./nav";

// Prefetch данных вероятного следующего экрана при наведении (§6.1)
const PREFETCH: Record<string, { key: unknown[]; path: string }> = {
  "/finance": { key: ["finance", "cash"], path: "/api/finance/cash" },
  "/inkassaciya": { key: ["inkassaciya"], path: "/api/inkassaciya" },
  "/supply": { key: ["supply", "requests"], path: "/api/supply/requests" },
};
function prefetch(to: string) {
  const p = PREFETCH[to];
  if (p) queryClient.prefetchQuery({ queryKey: p.key, queryFn: () => api.get(p.path) });
}

// Code-splitting по маршрутам (§6.4) — ленивая загрузка страниц
const DashboardPage = lazy(() => import("@/pages/dashboard/DashboardPage"));
const FinancePage = lazy(() => import("@/pages/finance/FinancePage"));
const InkassaciyaPage = lazy(() => import("@/pages/inkassaciya/InkassaciyaPage"));
const SupplyPage = lazy(() => import("@/pages/supply/SupplyPage"));
const ZastroyshchikPage = lazy(() => import("@/pages/business/ZastroyshchikPage"));
const ProektnayaPage = lazy(() => import("@/pages/business/ProektnayaPage"));
const BetonPage = lazy(() => import("@/pages/business/BetonPage"));
const ShchebenPage = lazy(() => import("@/pages/business/ShchebenPage"));
const OwnersPage = lazy(() => import("@/pages/owners/OwnersPage"));
const AuditPage = lazy(() => import("@/pages/audit/AuditPage"));

function Brand() {
  return (
    <div className="flex items-center gap-2">
      <div className="grid h-9 w-9 place-items-center rounded-md bg-brand font-bold text-white">A</div>
      <div className="leading-tight">
        <div className="text-sm font-bold text-ink">ARKAND</div>
        <div className="text-[10px] text-neutral-500">Финансовая CRM</div>
      </div>
    </div>
  );
}

export function AppShell() {
  const auth = useAuth();
  const [moreOpen, setMoreOpen] = useState(false);
  const items = useMemo(() => NAV.filter((n) => n.show(auth)), [auth]);
  const primary = items.slice(0, 4);
  const rest = items.slice(4);

  const linkCls = ({ isActive }: { isActive: boolean }) =>
    cn(
      "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors",
      isActive ? "bg-crimson-50 text-brand" : "text-neutral-600 hover:bg-neutral-100",
    );

  return (
    <div className="flex min-h-screen bg-paper">
      {/* Сайдбар (десктоп) */}
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-neutral-100 bg-white p-3 md:flex">
        <div className="px-2 py-3">
          <Brand />
        </div>
        <nav className="mt-2 flex flex-1 flex-col gap-1 overflow-y-auto">
          {items.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.to === "/"} className={linkCls} onMouseEnter={() => prefetch(n.to)}>
              <span className="text-lg">{n.icon}</span>
              {n.label}
            </NavLink>
          ))}
        </nav>
        <UserBox />
      </aside>

      {/* Контент */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Шапка (мобайл) */}
        <header
          className="sticky top-0 z-30 flex items-center justify-between border-b border-neutral-100 bg-white px-4 py-3 md:hidden"
          style={{ paddingTop: "max(0.75rem, env(safe-area-inset-top))" }}
        >
          <Brand />
          <UserButton />
        </header>

        <main className="min-w-0 flex-1 px-3 pb-24 pt-4 md:px-6 md:pb-8">
          <Suspense fallback={<TableSkeleton rows={6} />}>
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/finance" element={<FinancePage />} />
              <Route path="/inkassaciya" element={<InkassaciyaPage />} />
              <Route path="/supply" element={<SupplyPage />} />
              <Route path="/zastroyshchik" element={<ZastroyshchikPage />} />
              <Route path="/proektnaya" element={<ProektnayaPage />} />
              <Route path="/beton" element={<BetonPage />} />
              <Route path="/shcheben" element={<ShchebenPage />} />
              <Route path="/owners" element={<OwnersPage />} />
              <Route path="/audit" element={<AuditPage />} />
              <Route path="*" element={<DashboardPage />} />
            </Routes>
          </Suspense>
        </main>
      </div>

      {/* Нижняя навигация (мобайл) */}
      <nav
        className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t border-neutral-100 bg-white md:hidden"
        style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
      >
        {primary.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            end={n.to === "/"}
            className={({ isActive }) =>
              cn("flex min-h-[56px] flex-col items-center justify-center gap-0.5 text-[10px]", isActive ? "text-brand" : "text-neutral-500")
            }
          >
            <span className="text-xl">{n.icon}</span>
            {n.label}
          </NavLink>
        ))}
        <button
          onClick={() => setMoreOpen(true)}
          className="flex min-h-[56px] flex-col items-center justify-center gap-0.5 text-[10px] text-neutral-500"
        >
          <span className="text-xl">⋯</span>
          Ещё
        </button>
      </nav>

      {/* Drawer «Ещё» (мобайл) */}
      {moreOpen && (
        <div className="fixed inset-0 z-40 md:hidden" onClick={() => setMoreOpen(false)}>
          <div className="absolute inset-0 bg-black/40" />
          <div
            className="absolute inset-x-0 bottom-0 rounded-t-lg bg-white p-3"
            style={{ paddingBottom: "calc(env(safe-area-inset-bottom) + 0.75rem)" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-neutral-200" />
            <div className="grid grid-cols-3 gap-2">
              {rest.map((n) => (
                <NavLink
                  key={n.to}
                  to={n.to}
                  onClick={() => setMoreOpen(false)}
                  className="flex flex-col items-center gap-1 rounded-md p-3 text-center text-xs text-neutral-600 hover:bg-neutral-100"
                >
                  <span className="text-2xl">{n.icon}</span>
                  {n.label}
                </NavLink>
              ))}
            </div>
            <div className="mt-3 border-t border-neutral-100 pt-3">
              <UserBox />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function UserBox() {
  const { user, logout } = useAuth();
  return (
    <div className="flex items-center justify-between gap-2 rounded-md bg-neutral-50 p-2">
      <div className="min-w-0">
        <div className="truncate text-sm font-medium text-ink">{user?.full_name}</div>
        <div className="truncate text-[11px] text-neutral-500">{user?.owner_type ?? user?.roles?.[0] ?? "сотрудник"}</div>
      </div>
      <button onClick={logout} className="shrink-0 rounded-md px-2 py-1 text-xs text-status-error hover:bg-status-error/10">
        Выход
      </button>
    </div>
  );
}

function UserButton() {
  const { user, logout } = useAuth();
  return (
    <button onClick={logout} aria-label="Выход" className="flex min-h-[44px] min-w-[44px] items-center justify-center gap-2 rounded-md px-2 py-1 text-sm text-neutral-600">
      <span className="grid h-9 w-9 place-items-center rounded-full bg-crimson-50 text-brand">
        {user?.full_name?.[0] ?? "?"}
      </span>
    </button>
  );
}
