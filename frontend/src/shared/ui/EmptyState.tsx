export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-neutral-200 bg-white/50 px-4 py-12 text-center">
      <div className="text-3xl">📭</div>
      <p className="font-medium text-ink">{title}</p>
      {hint && <p className="max-w-xs text-sm text-neutral-500">{hint}</p>}
      {action}
    </div>
  );
}
