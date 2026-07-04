import { useRef } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";

interface Props<T> {
  items: T[];
  keyField: (row: T) => string;
  renderRow: (row: T) => React.ReactNode;
  estimateSize?: number;
  height?: number;
}

/**
 * Виртуализация длинных списков (§6.4) — рендерятся только видимые строки.
 * Используется для потенциально длинных списков (аудит-лог, движения кассы).
 */
export function VirtualList<T>({ items, keyField, renderRow, estimateSize = 60, height = 520 }: Props<T>) {
  const parentRef = useRef<HTMLDivElement>(null);
  const v = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => estimateSize,
    overscan: 8,
  });

  return (
    <div ref={parentRef} style={{ height, overflow: "auto" }} className="rounded-lg border border-neutral-100 bg-white">
      <div style={{ height: v.getTotalSize(), position: "relative", width: "100%" }}>
        {v.getVirtualItems().map((vi) => (
          <div
            key={keyField(items[vi.index])}
            style={{ position: "absolute", top: 0, left: 0, width: "100%", transform: `translateY(${vi.start}px)` }}
          >
            {renderRow(items[vi.index])}
          </div>
        ))}
      </div>
    </div>
  );
}
