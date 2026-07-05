// Access-токен хранится ТОЛЬКО в памяти (не в localStorage/sessionStorage — недоступен из DevTools/XSS-дампов).
// Refresh-токен живёт в httpOnly Secure cookie и недоступен JS вовсе.
let accessToken: string | null = null;

export const tokens = {
  access: (): string | null => accessToken,
  setAccess: (t: string | null): void => {
    accessToken = t;
  },
  clear: (): void => {
    accessToken = null;
  },
};
