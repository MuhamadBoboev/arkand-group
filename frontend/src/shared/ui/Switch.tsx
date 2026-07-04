import { cn } from "@/shared/lib/cn";

interface Props {
  checked: boolean;
  onChange: (v: boolean) => void;
  label?: string;
  disabled?: boolean;
}

export function Switch({ checked, onChange, label, disabled }: Props) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className="inline-flex min-h-[44px] items-center gap-3 disabled:opacity-50"
    >
      <span
        className={cn(
          "relative h-6 w-11 rounded-pill transition-colors",
          checked ? "bg-brand" : "bg-neutral-300",
        )}
      >
        <span
          className={cn(
            "absolute top-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition-transform",
            checked ? "translate-x-[22px]" : "translate-x-0.5",
          )}
        />
      </span>
      {label && <span className="text-sm text-ink">{label}</span>}
    </button>
  );
}
