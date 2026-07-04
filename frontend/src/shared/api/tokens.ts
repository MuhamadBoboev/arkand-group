// Хранилище JWT (access+refresh) в localStorage. Общий источник для api-клиента и auth-стора.
const A = "arkand_access";
const R = "arkand_refresh";

export const tokens = {
  access: (): string | null => localStorage.getItem(A),
  refresh: (): string | null => localStorage.getItem(R),
  set: (access: string, refresh: string): void => {
    localStorage.setItem(A, access);
    localStorage.setItem(R, refresh);
  },
  clear: (): void => {
    localStorage.removeItem(A);
    localStorage.removeItem(R);
  },
};
