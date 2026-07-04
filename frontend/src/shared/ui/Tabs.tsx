import { cn } from "@/shared/lib/cn";

interface Props {
  items: { key: string; label: string }[];
  value: string;
  onChange: (key: string) => void;
}

export function Tabs({ items, value, onChange }: Props) {
  return (
    <div className="-mx-1 flex gap-1 overflow-x-auto pb-1">
      {items.map((it) => (
        <button
          key={it.key}
          onClick={() => onChange(it.key)}
          className={cn(
            "whitespace-nowrap rounded-pill px-4 py-2 text-sm font-medium transition-colors",
            value === it.key ? "bg-brand text-white" : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200",
          )}
        >
          {it.label}
        </button>
      ))}
    </div>
  );
}
