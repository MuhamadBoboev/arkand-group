import { useState } from "react";
import { api } from "@/shared/api/client";
import { useApiMutation, useList } from "@/shared/api/hooks";
import { useAuth } from "@/shared/model/auth.store";
import { Amount, Button, Card, EmptyState, PageTitle, ResourceList, StatusChip, Table, Tabs, VirtualList, type Column } from "@/shared/ui";

export default function AuditPage() {
  const { can } = useAuth();
  const [tab, setTab] = useState("log");
  const canWrite = can("audit", "create");

  return (
    <div>
      <PageTitle title="Отдел проверки" subtitle="Только чтение по системам; акты и эскалация троим (§9.8)" />
      <div className="mb-4">
        <Tabs value={tab} onChange={setTab} items={[
          { key: "log", label: "Аудит-лог" }, { key: "reconcile", label: "Сверка касс" }, { key: "acts", label: "Акты" },
        ]} />
      </div>

      {tab === "log" && <AuditLogTab />}
      {tab === "reconcile" && <ReconcileTab />}
      {tab === "acts" && <ActsTab canWrite={canWrite} />}
    </div>
  );
}

function AuditLogTab() {
  const { data, isLoading } = useList(["audit", "log"], "/api/audit/log");
  const items = (data as any)?.items ?? [];
  if (isLoading) return <Card>Загрузка…</Card>;
  if (!items.length) return <EmptyState title="Записей нет" />;
  // Виртуализация длинного неизменяемого журнала (§6.4)
  return (
    <VirtualList
      items={items}
      keyField={(r: any) => r.id}
      estimateSize={64}
      renderRow={(r: any) => (
        <div className="flex items-center justify-between gap-3 border-b border-neutral-50 px-4 py-3">
          <div className="min-w-0">
            <div className="truncate text-sm text-ink">
              <span className="font-medium">{r.action}</span> · {r.resource}
            </div>
            <div className="text-xs text-neutral-500">{new Date(r.at).toLocaleString("ru-RU")}</div>
          </div>
          <span className="shrink-0 font-num text-xs text-neutral-400">{r.user_id?.slice(0, 8) ?? "—"}</span>
        </div>
      )}
    />
  );
}

function ReconcileTab() {
  const { data } = useList(["audit", "reconcile"], "/api/audit/reconcile/cash");
  const columns: Column<any>[] = [
    { key: "cash_name", header: "Касса" },
    { key: "system_balance", header: "Система", align: "right", render: (r) => <Amount value={r.system_balance} /> },
    { key: "last_inkassaciya_status", header: "Инкассация", render: (r) => (r.last_inkassaciya_status ? <StatusChip status={r.last_inkassaciya_status} /> : "—") },
    { key: "last_discrepancy", header: "Расхождение", align: "right", render: (r) => (r.last_discrepancy ? <Amount value={r.last_discrepancy} showSign /> : "—") },
  ];
  return <Table columns={columns} rows={(data as any)?.items ?? []} keyField={(r) => r.cash_id} cardTitle={(r) => r.cash_name} empty={<Card><span className="text-sm text-neutral-500">Нет касс</span></Card>} />;
}

function ActsTab({ canWrite }: { canWrite: boolean }) {
  const escalate = useApiMutation({
    mutationFn: (actId: string) => api.post("/api/audit/escalations", { act_id: actId, reason: "Нарушение по акту проверки" }),
    invalidate: [["audit"]],
    successMsg: "Эскалация направлена всем троим владельцам",
  });
  const resolve = useApiMutation({
    mutationFn: (actId: string) => api.post(`/api/audit/acts/${actId}/resolve`),
    invalidate: [["audit", "acts"]],
    successMsg: "Акт отмечен устранённым",
  });

  const columns: Column<any>[] = [
    { key: "title", header: "Акт" },
    { key: "status", header: "Статус", render: (r) => <StatusChip status={r.status} /> },
    {
      key: "act", header: "", align: "right",
      render: (r) =>
        canWrite ? (
          <div className="flex justify-end gap-1">
            <Button size="sm" variant="danger" onClick={() => escalate.mutate(r.id)}>Эскалация</Button>
            {r.status !== "resolved" && <Button size="sm" variant="ghost" onClick={() => resolve.mutate(r.id)}>Устранено</Button>}
          </div>
        ) : null,
    },
  ];

  return (
    <ResourceList
      queryKey={["audit", "acts"]}
      listPath="/api/audit/acts"
      keyField={(r: any) => r.id}
      cardTitle={(r: any) => r.title}
      columns={columns}
      create={canWrite ? { path: "/api/audit/acts", title: "Новый акт проверки", buttonLabel: "Акт", fields: [{ name: "title", label: "Название" }, { name: "summary", label: "Описание" }] } : undefined}
    />
  );
}
