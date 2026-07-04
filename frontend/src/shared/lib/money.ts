/** Форматирование сумм: табличные цифры, разряды (§4.4). */
export function formatMoney(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(n)) return "—";
  return n.toLocaleString("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export type MoneyTone = "income" | "expense" | "balance";

/**
 * Правило §4.2 «Бренд ≠ Деньги»: доход зелёный, расход/минус — сигнальный красный
 * (--money-expense), НЕ вишнёвый бренд-цвет.
 */
export function moneyTone(value: number | string, kind?: "income" | "expense"): MoneyTone {
  const n = typeof value === "string" ? Number(value) : value;
  if (kind === "income") return "income";
  if (kind === "expense") return "expense";
  if (n > 0) return "income";
  if (n < 0) return "expense";
  return "balance";
}

export const moneyClass: Record<MoneyTone, string> = {
  income: "text-money-income",
  expense: "text-money-expense",
  balance: "text-money-balance",
};
