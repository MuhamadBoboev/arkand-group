import { QueryClient } from "@tanstack/react-query";
import { wsClient, type WsEvent } from "./ws";
import { useAuth } from "@/shared/model/auth.store";

/** Настройки кеша (§6.1): справочники живут дольше, деньги — короче + инвалидация по WS. */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 1000 * 60 * 60,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

/**
 * Мост реалтайма (§6.2, §6.3): WS-событие патчит/инвалидирует соответствующие Query-кеши —
 * мгновенная синхронизация между отделами без перезагрузки.
 */
/** Каналы, на которые подписывается клиент (бэк дополнительно фильтрует по правам §12). */
function channelsForUser(): string[] {
  const u = useAuth.getState().user;
  if (!u) return [];
  const chans = new Set<string>(["finance", "supply", "audit", `employee:${u.id}`]);
  if (u.is_owner) chans.add("owners");
  u.businesses.forEach((b) => chans.add(`business:${b}`));
  return [...chans];
}

let started = false;
export function startRealtimeSync(): void {
  if (started) return;
  started = true;

  // Подписка на каналы (критично §12: без subscribe клиент не получает событий)
  wsClient.connect();
  wsClient.subscribe(channelsForUser());

  // Ресинк кешей после переподключения — пропущенные за обрыв события (§12)
  wsClient.onReconnect(() => {
    ["finance", "inkassaciya", "analytics", "supply", "stock", "orders", "approvals", "tasks", "audit"].forEach(
      (k) => queryClient.invalidateQueries({ queryKey: [k] }),
    );
  });

  wsClient.onEvent((e: WsEvent) => {
    const inv = (key: unknown[]) => queryClient.invalidateQueries({ queryKey: key });
    const ch = e.channel;
    if (ch.startsWith("cash:") || ch === "finance") {
      inv(["finance"]);
      inv(["inkassaciya"]);
      inv(["analytics"]);
    } else if (ch.startsWith("business:")) {
      const bid = ch.split(":", 2)[1];
      inv(["business", bid]);
      inv(["orders"]);
      inv(["stock"]);
      inv(["supply"]);
    } else if (ch === "supply") {
      inv(["supply"]);
      inv(["stock"]);
    } else if (ch === "owners") {
      inv(["approvals"]);
      inv(["analytics"]);
      inv(["tasks"]);
    } else if (ch === "audit") {
      inv(["audit"]);
    }
  });
}
