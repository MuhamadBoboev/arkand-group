import { cn } from "@/shared/lib/cn";

export type BadgeTone = "success" | "warning" | "error" | "info" | "neutral";

const tones: Record<BadgeTone, string> = {
  success: "bg-status-success/10 text-status-success",
  warning: "bg-status-warning/10 text-status-warning",
  error: "bg-status-error/10 text-status-error",
  info: "bg-status-info/10 text-status-info",
  neutral: "bg-neutral-100 text-neutral-600",
};

export function Badge({ tone = "neutral", children }: { tone?: BadgeTone; children: React.ReactNode }) {
  return (
    <span className={cn("inline-flex items-center rounded-pill px-2.5 py-1 text-xs font-medium", tones[tone])}>
      {children}
    </span>
  );
}

// Маппинг статусов домена → тон (§4.3)
const STATUS_TONE: Record<string, BadgeTone> = {
  accepted: "success",
  approved: "success",
  done: "success",
  resolved: "success",
  in_transit: "info",
  pending: "warning",
  pending_approval: "warning",
  new: "info",
  open: "warning",
  in_cash: "neutral",
  discrepancy: "error",
  rejected: "error",
  cancelled: "error",
  defect: "error",
};

const STATUS_LABEL: Record<string, string> = {
  accepted: "принято",
  approved: "согласовано",
  rejected: "отклонено",
  pending: "ожидает",
  pending_approval: "ждёт согласования",
  in_transit: "в пути",
  in_cash: "в кассе",
  discrepancy: "расхождение",
  new: "новый",
  open: "открыто",
  done: "выполнено",
  resolved: "устранено",
  cancelled: "отменён",
  partial: "частично",
  defect: "брак",
  in_production: "в производстве",
  shipped: "отгружено",
};

export function StatusChip({ status }: { status: string }) {
  return <Badge tone={STATUS_TONE[status] ?? "neutral"}>{STATUS_LABEL[status] ?? status}</Badge>;
}
