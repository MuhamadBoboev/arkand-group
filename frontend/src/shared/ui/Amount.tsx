import { cn } from "@/shared/lib/cn";
import { formatMoney, moneyClass, moneyTone } from "@/shared/lib/money";

interface Props {
  value: number | string;
  kind?: "income" | "expense";
  showSign?: boolean;
  className?: string;
}

/**
 * Компонент суммы с правилом §4.2 (Бренд ≠ Деньги): доход зелёный, расход/минус —
 * сигнальный красный, нейтраль — warm-ink. Табличные цифры, выравнивание по правому краю.
 */
export function Amount({ value, kind, showSign, className }: Props) {
  const tone = moneyTone(value, kind);
  const n = typeof value === "string" ? Number(value) : value;
  const sign = kind === "income" || n > 0 ? "+" : kind === "expense" || n < 0 ? "−" : "";
  const abs = Math.abs(n);
  return (
    <span className={cn("font-num tabular-nums text-right", moneyClass[tone], className)}>
      {showSign && sign} {formatMoney(kind ? abs : value)} c.
    </span>
  );
}
