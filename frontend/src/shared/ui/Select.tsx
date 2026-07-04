import { forwardRef, type SelectHTMLAttributes } from "react";
import { cn } from "@/shared/lib/cn";

interface Props extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  options: { value: string; label: string }[];
  placeholder?: string;
}

export const Select = forwardRef<HTMLSelectElement, Props>(function Select(
  { label, error, options, placeholder, className, id, ...rest },
  ref,
) {
  const selId = id ?? rest.name;
  return (
    <label className="block" htmlFor={selId}>
      {label && <span className="mb-1 block text-sm font-medium text-ink">{label}</span>}
      <select
        ref={ref}
        id={selId}
        {...rest}
        className={cn(
          "w-full min-h-[44px] rounded-md border bg-white px-3 text-[15px] text-ink outline-none",
          "focus:ring-2 focus:ring-brand/40",
          error ? "border-status-error" : "border-neutral-200 focus:border-brand",
          className,
        )}
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      {error && <span className="mt-1 block text-xs text-status-error">{error}</span>}
    </label>
  );
});
