import { type ReactNode } from "react";
import { cn } from "@/shared/lib/cn";
import { Card } from "./Card";

export interface Column<T> {
  key: string;
  header: string;
  render?: (row: T) => ReactNode;
  align?: "left" | "right";
  hideOnMobile?: boolean;
}

interface Props<T> {
  columns: Column<T>[];
  rows: T[];
  keyField: (row: T) => string;
  cardTitle?: (row: T) => ReactNode;
  onRowClick?: (row: T) => void;
  empty?: ReactNode;
}

/**
 * Адаптивная таблица (§5.2): на md+ — таблица, на мобиле (<md) — карточки
 * (одна запись = одна карточка). Никакого горизонтального скролла на телефоне.
 */
export function Table<T>({ columns, rows, keyField, cardTitle, onRowClick, empty }: Props<T>) {
  const cell = (col: Column<T>, row: T) => (col.render ? col.render(row) : (row as any)[col.key]);

  if (rows.length === 0 && empty) return <>{empty}</>;

  return (
    <>
      {/* Desktop / планшет */}
      <div className="hidden overflow-hidden rounded-lg border border-neutral-100 bg-white md:block">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-neutral-100 bg-neutral-50 text-left text-neutral-500">
              {columns.map((c) => (
                <th key={c.key} className={cn("px-4 py-3 font-medium", c.align === "right" && "text-right")}>
                  {c.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={keyField(row)}
                onClick={() => onRowClick?.(row)}
                className={cn("border-b border-neutral-50 last:border-0", onRowClick && "cursor-pointer hover:bg-neutral-50")}
              >
                {columns.map((c) => (
                  <td key={c.key} className={cn("px-4 py-3 text-ink", c.align === "right" && "text-right")}>
                    {cell(c, row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Мобильные карточки (одна запись = одна карточка) */}
      <div className="flex flex-col gap-3 md:hidden">
        {rows.map((row) => (
          <Card key={keyField(row)} className={cn(onRowClick && "active:bg-neutral-50")}>
            <div onClick={() => onRowClick?.(row)}>
              {cardTitle && <div className="mb-2 font-semibold text-ink">{cardTitle(row)}</div>}
              <dl className="flex flex-col gap-1.5">
                {columns.filter((c) => !c.hideOnMobile).map((c) => (
                  <div key={c.key} className="flex items-start justify-between gap-3">
                    <dt className="text-xs text-neutral-500">{c.header}</dt>
                    <dd className="text-right text-sm text-ink">{cell(c, row)}</dd>
                  </div>
                ))}
              </dl>
            </div>
          </Card>
        ))}
      </div>
    </>
  );
}
