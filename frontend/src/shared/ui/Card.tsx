import { cn } from "@/shared/lib/cn";

export function Card({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <div className={cn("rounded-lg border border-neutral-100 bg-white p-4 shadow-sm", className)}>{children}</div>
  );
}

export function StatCard({ label, value, tone, sub }: { label: string; value: React.ReactNode; tone?: string; sub?: string }) {
  return (
    <Card className="flex flex-col gap-1">
      <span className="text-xs font-medium uppercase tracking-wide text-neutral-500">{label}</span>
      <span className={cn("font-num text-2xl font-semibold tabular-nums", tone)}>{value}</span>
      {sub && <span className="text-xs text-neutral-500">{sub}</span>}
    </Card>
  );
}
