import { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api, ApiError } from "@/shared/api/client";
import { queryClient } from "@/shared/api/query";
import { useList } from "@/shared/api/hooks";
import { useAuth } from "@/shared/model/auth.store";
import {
  Amount, Button, Card, Input, Modal, PageTitle, Select, StatusChip, Table, TableSkeleton, Tabs, toast, type Column,
} from "@/shared/ui";

type Cash = { id: string; name: string; business_id: string; balance: string };
type Movement = { id: string; kind: string; amount: string; article?: string; status: string; is_reversal: boolean; reversed: boolean; created_at: string };

export default function FinancePage() {
  const { can } = useAuth();
  const { data: cashData, isLoading: cashLoading } = useList<Cash>(["finance", "cash"], "/api/finance/cash");
  const cashes = cashData?.items ?? [];
  const [cashId, setCashId] = useState<string>("");
  const activeCash = cashId || cashes[0]?.id || "";
  const movKey = ["finance", "movements", activeCash];

  const { data: movData, isLoading: movLoading } = useList<Movement>(movKey, `/api/finance/movements?cash_id=${activeCash}`, !!activeCash);

  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ kind: "income", amount: 0, article: "" });
  const [reverseId, setReverseId] = useState<string | null>(null);
  const [reason, setReason] = useState("");

  // Оптимистичное создание проводки (§6.2): мгновенно в UI → бэк → WS-broadcast; при ошибке откат
  const createMut = useMutation({
    mutationFn: (v: typeof form) => api.post("/api/finance/movements", { cash_id: activeCash, ...v }),
    onMutate: async (v) => {
      await queryClient.cancelQueries({ queryKey: movKey });
      const prevMov = queryClient.getQueryData<any>(movKey);
      const prevCash = queryClient.getQueryData<any>(["finance", "cash"]);
      const optimistic: Movement = {
        id: "optimistic-" + Date.now(), kind: v.kind, amount: String(v.amount), article: v.article,
        status: "in_cash", is_reversal: false, reversed: false, created_at: new Date().toISOString(),
      };
      queryClient.setQueryData(movKey, (o: any) => (o ? { ...o, items: [optimistic, ...o.items], total: o.total + 1 } : o));
      queryClient.setQueryData(["finance", "cash"], (o: any) =>
        o ? { ...o, items: o.items.map((c: Cash) => (c.id === activeCash ? { ...c, balance: String(Number(c.balance) + (v.kind === "income" ? 1 : -1) * v.amount) } : c)) } : o,
      );
      return { prevMov, prevCash };
    },
    onError: (e, _v, ctx) => {
      if (ctx) {
        queryClient.setQueryData(movKey, ctx.prevMov);
        queryClient.setQueryData(["finance", "cash"], ctx.prevCash);
      }
      toast.error(e instanceof ApiError ? e.message : "Ошибка проводки");
    },
    onSuccess: () => { toast.success("Проводка добавлена"); setOpen(false); setForm({ kind: "income", amount: 0, article: "" }); },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["finance"] }),
  });

  const reverseMut = useMutation({
    mutationFn: (id: string) => api.post(`/api/finance/movements/${id}/reverse`, { reason }),
    onSuccess: () => { toast.success("Сторно проведено"); setReverseId(null); setReason(""); queryClient.invalidateQueries({ queryKey: ["finance"] }); },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Ошибка сторно"),
  });

  const columns: Column<Movement>[] = useMemo(() => [
    { key: "article", header: "Статья", render: (m) => m.article || (m.is_reversal ? "Сторно" : "—") },
    { key: "status", header: "Статус", render: (m) => <StatusChip status={m.status} /> },
    { key: "amount", header: "Сумма", align: "right", render: (m) => <Amount value={m.amount} kind={m.kind as any} showSign /> },
    {
      key: "act", header: "", align: "right", hideOnMobile: false,
      render: (m) =>
        can("cash", "update_via_reversal") && !m.reversed && !m.is_reversal ? (
          <Button size="sm" variant="ghost" onClick={() => setReverseId(m.id)}>Сторно</Button>
        ) : m.reversed ? <span className="text-xs text-neutral-400">сторнирована</span> : null,
    },
  ], [can]);

  const balance = cashes.find((c) => c.id === activeCash)?.balance ?? "0";

  return (
    <div>
      <PageTitle
        title="Финансы"
        subtitle="Кассы, проводки, сторно (append-only §7.1)"
        action={can("cash", "create") && activeCash ? <Button onClick={() => setOpen(true)}>+ Проводка</Button> : undefined}
      />

      {cashLoading ? (
        <TableSkeleton rows={3} />
      ) : (
        <>
          <div className="mb-4 flex items-center gap-3">
            <Tabs items={cashes.map((c) => ({ key: c.id, label: c.name }))} value={activeCash} onChange={setCashId} />
          </div>
          <Card className="mb-4 flex items-center justify-between">
            <span className="text-sm text-neutral-500">Баланс кассы</span>
            <Amount value={balance} className="text-lg font-semibold" />
          </Card>

          {movLoading ? (
            <TableSkeleton />
          ) : (
            <Table columns={columns} rows={movData?.items ?? []} keyField={(m) => m.id}
              cardTitle={(m) => m.article || "Проводка"} empty={<Card><span className="text-sm text-neutral-500">Проводок пока нет</span></Card>} />
          )}
        </>
      )}

      {/* Модалка новой проводки */}
      <Modal open={open} onClose={() => setOpen(false)} title="Новая проводка"
        footer={<Button block loading={createMut.isPending} onClick={() => createMut.mutate(form)}>Провести</Button>}>
        <div className="flex flex-col gap-3">
          <Select label="Тип" value={form.kind} onChange={(e) => setForm((s) => ({ ...s, kind: e.target.value }))}
            options={[{ value: "income", label: "Доход (+)" }, { value: "expense", label: "Расход (−)" }]} />
          <Input label="Сумма" type="number" inputMode="decimal" value={form.amount || ""} onChange={(e) => setForm((s) => ({ ...s, amount: Number(e.target.value) }))} />
          <Input label="Статья" value={form.article} onChange={(e) => setForm((s) => ({ ...s, article: e.target.value }))} placeholder="Напр. Продажа" />
        </div>
      </Modal>

      {/* Модалка сторно */}
      <Modal open={!!reverseId} onClose={() => setReverseId(null)} title="Сторно проводки"
        footer={<Button block variant="danger" loading={reverseMut.isPending} onClick={() => reverseId && reverseMut.mutate(reverseId)}>Провести сторно</Button>}>
        <p className="mb-3 text-sm text-neutral-500">Проведённую операцию нельзя изменить — только обратное видимое сторно (§7.1).</p>
        <Input label="Причина" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Причина исправления" />
      </Modal>
    </div>
  );
}
