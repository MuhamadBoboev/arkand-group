import { forwardRef, useState, type InputHTMLAttributes } from "react";
import { LuEye, LuEyeOff } from "react-icons/lu";
import { cn } from "@/shared/lib/cn";

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
}

export const Input = forwardRef<HTMLInputElement, Props>(function Input(
  { label, error, hint, className, id, type = "text", ...rest },
  ref,
) {
  const inputId = id ?? rest.name;
  const isPassword = type === "password";
  const [reveal, setReveal] = useState(false);
  const effectiveType = isPassword && reveal ? "text" : type;

  return (
    <label className="block" htmlFor={inputId}>
      {label && <span className="mb-1 block text-sm font-medium text-ink">{label}</span>}
      <div className="relative">
        <input
          ref={ref}
          id={inputId}
          type={effectiveType}
          {...rest}
          className={cn(
            "w-full min-h-[44px] rounded-md border bg-white px-3 text-[15px] text-ink outline-none transition",
            "placeholder:text-neutral-400 focus:ring-2 focus:ring-brand/40",
            isPassword && "pr-12",
            error ? "border-status-error" : "border-neutral-200 focus:border-brand",
            className,
          )}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setReveal((v) => !v)}
            aria-label={reveal ? "Скрыть пароль" : "Показать пароль"}
            title={reveal ? "Скрыть пароль" : "Показать пароль"}
            className="absolute right-1 top-1/2 grid h-10 w-10 -translate-y-1/2 place-items-center rounded-md text-neutral-400 hover:text-ink hover:bg-neutral-100"
          >
            {reveal ? <LuEyeOff size={18} /> : <LuEye size={18} />}
          </button>
        )}
      </div>
      {error ? (
        <span className="mt-1 block text-xs text-status-error">{error}</span>
      ) : hint ? (
        <span className="mt-1 block text-xs text-neutral-500">{hint}</span>
      ) : null}
    </label>
  );
});
