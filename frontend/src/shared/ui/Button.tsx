import { type ButtonHTMLAttributes } from "react";
import { cn } from "@/shared/lib/cn";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "md" | "sm";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  block?: boolean;
}

const variants: Record<Variant, string> = {
  // Вишнёвый бренд — только кнопки/акценты (§4.2)
  primary: "bg-brand text-white hover:bg-deep-maroon shadow-sm",
  secondary: "bg-white text-ink border border-neutral-200 hover:bg-neutral-50",
  ghost: "bg-transparent text-ink hover:bg-neutral-100",
  danger: "bg-status-error text-white hover:brightness-95",
};

export function Button({ variant = "primary", size = "md", loading, block, className, children, disabled, ...rest }: Props) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors",
        "min-h-[44px] disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-brand/40",
        size === "md" ? "px-4 text-[15px]" : "px-3 text-sm",
        block && "w-full",
        variants[variant],
        className,
      )}
    >
      {loading && <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />}
      {children}
    </button>
  );
}
