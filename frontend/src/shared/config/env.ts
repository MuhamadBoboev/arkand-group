// В dev VITE_API_URL пуст → относительные пути (Vite-прокси). В проде — URL Railway.
export const API_URL = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

export function apiUrl(path: string): string {
  return `${API_URL}${path}`;
}

export function wsUrl(): string {
  if (API_URL) return API_URL.replace(/^http/, "ws") + "/ws";
  const proto = location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${location.host}/ws`;
}
