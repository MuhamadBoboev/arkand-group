import { type ReactNode, useEffect } from "react";
import { LuX } from "react-icons/lu";
import { cn } from "@/shared/lib/cn";

interface Props {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  footer?: ReactNode;
}

/**
 * Модалка (§5.2): на десктопе — центрированный диалог, на мобиле — полноэкранный
 * bottom-drawer снизу. Учитывает safe-area.
 */
export function Modal({ open, onClose, title, children, footer }: Props) {
  useEffect(() => {
    if (!open) return;
    const onEsc = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onEsc);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onEsc);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center md:items-center" role="dialog" aria-modal="true">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div
        className={cn(
          "relative z-10 w-full max-h-[92vh] overflow-y-auto bg-white shadow-lg",
          "rounded-t-lg md:w-full md:max-w-lg md:rounded-lg",
          "animate-in",
        )}
        style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
      >
        {title && (
          <div className="sticky top-0 flex items-center justify-between border-b border-neutral-100 bg-white px-4 py-3">
            <h3 className="text-base font-semibold text-ink">{title}</h3>
            <button onClick={onClose} className="grid h-11 w-11 place-items-center rounded-md text-neutral-500 hover:bg-neutral-100" aria-label="Закрыть">
              <LuX size={20} />
            </button>
          </div>
        )}
        <div className="p-4">{children}</div>
        {footer && <div className="sticky bottom-0 border-t border-neutral-100 bg-white p-4">{footer}</div>}
      </div>
    </div>
  );
}
