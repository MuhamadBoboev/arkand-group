import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api, ApiError } from "@/shared/api/client";
import { queryClient } from "@/shared/api/query";
import { useList } from "@/shared/api/hooks";
import { useAuth } from "@/shared/model/auth.store";
import { Amount, Button, Card, Input, Modal, PageTitle, Select, StatusChip, Table, TableSkeleton, toast, type Column } from "@/shared/ui";

type Ink = { id: string; cash_id: string; calc_amount: string; fact_amount?: string; discrepancy?: string; status: string };
type Cash = { id: string; name: string };

export default function InkassaciyaPage() {
  const { can } = useAuth();
  const { data, isLoading } = useList<Ink>(["inkassaciya"], "/api/inkassaciya");
  const { data: cashData } = useList<Cash>(["finance", "cash"], "/api/finance/cash", can("inkassaciya", "create"));

  const [wizard, setWizard] = useState(false);
  const [cashId, setCashId] = useState("");
  const [current, setCurrent] = useState<Ink | null>(null);
  const [fact, setFact] = useState<number>(0);

  const [acceptInk, setAcceptInk] = useState<Ink | null>(null);
  const [accepted, setAccepted] = useState<number>(0);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["inkassaciya"] });

  const startMut = useMutation({
    mutationFn: () => api.post("/api/inkassaciya/start", { cash_id: cashId }),
    onSuccess: (ink: Ink) => { setCurrent(ink); setFact(Number(ink.calc_amount)); invalidate(); },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Ошибка"),
  });
  const factMut = useMutation({
    mutationFn: () => api.post(`/api/inkassaciya/${current!.id}/fact`, { fact_amount: fact }),
    onSuccess: () => { toast.success("Деньги переведены в путь"); setWizard(false); setCurrent(null); invalidate(); },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Ошибка"),
  });
  const acceptMut = useMutation({
    mutationFn: () => api.post(`/api/inkassaciya/${acceptInk!.id}/accept`, { accepted_amount: accepted }),
    onSuccess: (r: Ink) => { toast.success(r.status === "accepted" ? "Принято" : "Зафиксировано расхождение"); setAcceptInk(null); invalidate(); },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Ошибка"),
  });

  const cashName = (id: string) => cashData?.items?.find((c) => c.id === id)?.name ?? id.slice(0, 8);

  const columns: Column<Ink>[] = [
    { key: "cash", header: "Касса", render: (r) => cashName(r.cash_id) },
    { key: "calc", header: "Расчёт", align: "right", render: (r) => <Amount value={r.calc_amount} /> },
    { key: "fact", header: "Факт", align: "right", render: (r) => (r.fact_amount ? <Amount value={r.fact_amount} /> : "—") },
    { key: "disc", header: "Расхождение", align: "right", render: (r) => (r.discrepancy && Number(r.discrepancy) !== 0 ? <Amount value={r.discrepancy} showSign /> : "—") },
    { key: "status", header: "Статус", render: (r) => <StatusChip status={r.status} /> },
    {
      key: "act", header: "", align: "right",
      render: (r) =>
        r.status === "in_transit" && can("inkassaciya", "confirm") ? (
          <Button size="sm" onClick={() => { setAcceptInk(r); setAccepted(Number(r.fact_amount ?? 0)); }}>Принять</Button>
        ) : null,
    },
  ];

  return (
    <div>
      <PageTitle title="Инкассация" subtitle="Двусторонняя: передал ≠ подтвердил (§9.6.1)"
        action={can("inkassaciya", "create") ? <Button onClick={() => { setWizard(true); setCurrent(null); setCashId(cashData?.items?.[0]?.id ?? ""); }}>+ Инкассация</Button> : undefined} />

      {isLoading ? <TableSkeleton /> : (
        <Table columns={columns} rows={data?.items ?? []} keyField={(r) => r.id}
          cardTitle={(r) => cashName(r.cash_id)} empty={<Card><span className="text-sm text-neutral-500">Инкассаций пока нет</span></Card>} />
      )}

      {/* Мастер: старт → факт */}
      <Modal open={wizard} onClose={() => setWizard(false)} title="Инкассация"
        footer={
          !current ? (
            <Button block loading={startMut.isPending} disabled={!cashId} onClick={() => startMut.mutate()}>Показать расчёт</Button>
          ) : (
            <Button block loading={factMut.isPending} onClick={() => factMut.mutate()}>Передать в путь</Button>
          )
        }>
        {!current ? (
          <Select label="Касса" value={cashId} onChange={(e) => setCashId(e.target.value)} placeholder="Выберите кассу"
            options={(cashData?.items ?? []).map((c) => ({ value: c.id, label: c.name }))} />
        ) : (
          <div className="flex flex-col gap-3">
            <Card className="flex items-center justify-between">
              <span className="text-sm text-neutral-500">Расчётный остаток (справочно)</span>
              <Amount value={current.calc_amount} />
            </Card>
            <Input label="Фактическая сумма (пересчёт)" type="number" inputMode="decimal" value={fact || ""} onChange={(e) => setFact(Number(e.target.value))} />
            <p className="text-xs text-neutral-500">Расхождение зафиксируется отдельной видимой операцией (недостача/излишек).</p>
          </div>
        )}
      </Modal>

      {/* Приём (другой пользователь) */}
      <Modal open={!!acceptInk} onClose={() => setAcceptInk(null)} title="Подтверждение приёма"
        footer={<Button block loading={acceptMut.isPending} onClick={() => acceptMut.mutate()}>Подтвердить</Button>}>
        <div className="flex flex-col gap-3">
          <Card className="flex items-center justify-between">
            <span className="text-sm text-neutral-500">Сумма в пути</span>
            <Amount value={acceptInk?.fact_amount ?? 0} />
          </Card>
          <Input label="Принятая сумма" type="number" inputMode="decimal" value={accepted || ""} onChange={(e) => setAccepted(Number(e.target.value))} />
          <p className="text-xs text-neutral-500">Подтверждает получатель — другой логин, не кассир (§7.6).</p>
        </div>
      </Modal>
    </div>
  );
}
