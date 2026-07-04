import { create } from "zustand";
import { cn } from "@/shared/lib/cn";

type Tone = "success" | "error" | "info";
type ToastItem = { id: number; message: string; tone: Tone };

type ToastState = {
  items: ToastItem[];
  add: (message: string, tone: Tone) => void;
  remove: (id: number) => void;
};

let counter = 0;

const useToastStore = create<ToastState>((set) => ({
  items: [],
  add: (message, tone) => {
    const id = ++counter;
    set((s) => ({ items: [...s.items, { id, message, tone }] }));
    setTimeout(() => set((s) => ({ items: s.items.filter((t) => t.id !== id) })), 4000);
  },
  remove: (id) => set((s) => ({ items: s.items.filter((t) => t.id !== id) })),
}));

export const toast = {
  success: (m: string) => useToastStore.getState().add(m, "success"),
  error: (m: string) => useToastStore.getState().add(m, "error"),
  info: (m: string) => useToastStore.getState().add(m, "info"),
};

const toneClass: Record<Tone, string> = {
  success: "border-l-status-success",
  error: "border-l-status-error",
  info: "border-l-status-info",
};

export function Toaster() {
  const { items, remove } = useToastStore();
  return (
    <div className="fixed inset-x-0 top-3 z-[60] flex flex-col items-center gap-2 px-3 md:inset-x-auto md:right-4">
      {items.map((t) => (
        <div
          key={t.id}
          onClick={() => remove(t.id)}
          className={cn(
            "w-full max-w-sm cursor-pointer rounded-md border-l-4 bg-white px-4 py-3 text-sm text-ink shadow-md",
            toneClass[t.tone],
          )}
        >
          {t.message}
        </div>
      ))}
    </div>
  );
}
