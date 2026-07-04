import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "@/shared/lib/cn";

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
}

export const Input = forwardRef<HTMLInputElement, Props>(function Input(
  { label, error, hint, className, id, ...rest },
  ref,
) {
  const inputId = id ?? rest.name;
  return (
    <label className="block" htmlFor={inputId}>
      {label && <span className="mb-1 block text-sm font-medium text-ink">{label}</span>}
      <input
        ref={ref}
        id={inputId}
        {...rest}
        className={cn(
          "w-full min-h-[44px] rounded-md border bg-white px-3 text-[15px] text-ink outline-none transition",
          "placeholder:text-neutral-400 focus:ring-2 focus:ring-brand/40",
          error ? "border-status-error" : "border-neutral-200 focus:border-brand",
          className,
        )}
      />
      {error ? (
        <span className="mt-1 block text-xs text-status-error">{error}</span>
      ) : hint ? (
        <span className="mt-1 block text-xs text-neutral-500">{hint}</span>
      ) : null}
    </label>
  );
});
