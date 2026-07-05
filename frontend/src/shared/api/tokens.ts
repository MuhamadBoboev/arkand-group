// Access-токен хранится ТОЛЬКО в памяти (не в localStorage/sessionStorage — недоступен из DevTools/XSS-дампов).
// Refresh-токен живёт в httpOnly Secure cookie и недоступен JS вовсе.
let accessToken: string | null = null;

// Одноразовая очистка токенов, оставшихся в localStorage от предыдущих версий.
try {
  localStorage.removeItem("arkand_access");
  localStorage.removeItem("arkand_refresh");
} catch {
  /* ignore */
}

export const tokens = {
  access: (): string | null => accessToken,
  setAccess: (t: string | null): void => {
    accessToken = t;
  },
  clear: (): void => {
    accessToken = null;
  },
};
