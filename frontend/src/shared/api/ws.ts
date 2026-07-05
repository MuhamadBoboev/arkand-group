import { wsUrl } from "@/shared/config/env";
import { tokens } from "./tokens";

export type WsEvent = { channel: string; type: string; payload: any; at: string };
type Handler = (e: WsEvent) => void;

/**
 * WS-клиент (§12): авторизация JWT, подписки по каналам, reconnect с backoff,
 * дедупликация событий, ресинк подписок после переподключения.
 */
class WsClient {
  private ws: WebSocket | null = null;
  private channels = new Set<string>();
  private handlers = new Set<Handler>();
  private reconnectHandlers = new Set<() => void>();
  private backoff = 1000;
  private seen = new Set<string>();
  private connected = false;
  private closedByUser = false;
  private hasConnectedBefore = false;

  connect(): void {
    if (this.ws || !tokens.access()) return;
    this.closedByUser = false;
    const ws = new WebSocket(wsUrl()); // без токена в URL — авторизуемся первым сообщением
    this.ws = ws;

    ws.onopen = () => {
      this.connected = true;
      this.backoff = 1000;
      // Авторизация JWT первым сообщением (токен не попадает в URL/логи)
      this.send({ type: "auth", token: tokens.access() });
      if (this.channels.size) this.send({ type: "subscribe", channels: [...this.channels] }); // ресинк подписок
      // После реконнекта (не первого коннекта) — ресинк кешей: события за время обрыва потеряны
      if (this.hasConnectedBefore) this.reconnectHandlers.forEach((h) => h());
      this.hasConnectedBefore = true;
    };
    ws.onmessage = (ev) => {
      let msg: any;
      try {
        msg = JSON.parse(ev.data);
      } catch {
        return;
      }
      if (msg.type === "connected" || msg.type === "subscribed" || msg.type === "pong") return;
      // дедупликация по (channel,type,at)
      const key = `${msg.channel}|${msg.type}|${msg.at}`;
      if (this.seen.has(key)) return;
      this.seen.add(key);
      if (this.seen.size > 500) this.seen = new Set([...this.seen].slice(-200));
      this.handlers.forEach((h) => h(msg as WsEvent));
    };
    ws.onclose = () => {
      this.connected = false;
      this.ws = null;
      if (!this.closedByUser) setTimeout(() => this.connect(), this.backoff = Math.min(this.backoff * 2, 15000));
    };
    ws.onerror = () => ws.close();
  }

  private send(obj: unknown): void {
    if (this.ws && this.connected) this.ws.send(JSON.stringify(obj));
  }

  subscribe(channels: string[]): void {
    channels.forEach((c) => this.channels.add(c));
    this.send({ type: "subscribe", channels });
  }

  onEvent(h: Handler): () => void {
    this.handlers.add(h);
    return () => this.handlers.delete(h);
  }

  /** Колбэк при переподключении — для ресинка Query-кешей (§12). */
  onReconnect(h: () => void): () => void {
    this.reconnectHandlers.add(h);
    return () => this.reconnectHandlers.delete(h);
  }

  close(): void {
    this.closedByUser = true;
    this.ws?.close();
    this.ws = null;
    this.channels.clear();
  }
}

export const wsClient = new WsClient();
