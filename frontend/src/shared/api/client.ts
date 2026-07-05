import { apiUrl } from "@/shared/config/env";
import { tokens } from "./tokens";

export class ApiError extends Error {
  code: string;
  details: unknown;
  status: number;
  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

type Options = { method?: string; body?: unknown; auth?: boolean; retry?: boolean };

/** Обновить access через refresh-cookie (httpOnly). Сырой fetch, чтобы не зациклить refresh. */
async function refreshAccess(): Promise<boolean> {
  try {
    const res = await fetch(apiUrl("/api/auth/refresh"), {
      method: "POST",
      credentials: "include", // отправляем httpOnly refresh-cookie
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) return false;
    const data = await res.json();
    tokens.setAccess(data.access_token);
    return true;
  } catch {
    return false;
  }
}

async function request<T = any>(path: string, opts: Options = {}): Promise<T> {
  const { method = "GET", body, auth = true, retry = true } = opts;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = tokens.access();
  if (auth && token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(apiUrl(path), {
    method,
    headers,
    credentials: "include", // cookie для refresh-сессии
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  // Истёк/отсутствует access → тихо обновляем через refresh-cookie и повторяем один раз
  if (res.status === 401 && auth && retry && (await refreshAccess())) {
    return request<T>(path, { ...opts, retry: false });
  }

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  const data = text ? JSON.parse(text) : null;

  if (!res.ok) {
    const err = data?.error ?? {};
    throw new ApiError(res.status, err.code ?? "error", err.message ?? "Ошибка запроса", err.details);
  }
  return data as T;
}

export const api = {
  get: <T = any>(path: string) => request<T>(path),
  post: <T = any>(path: string, body?: unknown, auth = true) => request<T>(path, { method: "POST", body, auth }),
  put: <T = any>(path: string, body?: unknown) => request<T>(path, { method: "PUT", body }),
  del: <T = any>(path: string) => request<T>(path, { method: "DELETE" }),
  refresh: refreshAccess,
};
