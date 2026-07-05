import { LuInbox } from "react-icons/lu";

export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-neutral-200 bg-white/50 px-4 py-12 text-center">
      <div className="grid h-12 w-12 place-items-center rounded-full bg-neutral-100 text-neutral-400">
        <LuInbox size={22} />
      </div>
      <p className="font-medium text-ink">{title}</p>
      {hint && <p className="max-w-xs text-sm text-neutral-500">{hint}</p>}
      {action}
    </div>
  );
}
