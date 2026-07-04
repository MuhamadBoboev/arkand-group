import { useState } from "react";
import { api } from "@/shared/api/client";
import { useApiMutation, useList, useOne } from "@/shared/api/hooks";
import { useAuth } from "@/shared/model/auth.store";
import { Amount, Button, Card, PageTitle, ResourceList, StatCard, StatusChip, Table, Tabs, type Column } from "@/shared/ui";

export default function OwnersPage() {
  const { user, can } = useAuth();
  const isOwner = !!user?.is_owner;
  const isTop = isOwner && (user?.owner_type === "sohib" || user?.owner_type === "iftikhor");
  const [tab, setTab] = useState(isTop ? "analytics" : "approvals");

  const items = [
    ...(isTop ? [{ key: "analytics", label: "Аналитика" }] : []),
    ...(can("approval", "approve") || isOwner ? [{ key: "approvals", label: "Согласования" }] : []),
    ...(isTop ? [{ key: "employees", label: "Сотрудники" }] : []),
    ...(isOwner ? [{ key: "tasks", label: "Задачи" }] : []),  // Довуд ставит задачи в своей зоне (§8.2)
    ...(isTop ? [{ key: "calendar", label: "Календарь" }] : []),
  ];

  return (
    <div>
      <PageTitle title="Надстройка владельцев" subtitle="Согласования троих, сотрудники, аналитика, календарь (§9.7)" />
      <div className="mb-4"><Tabs value={tab} onChange={setTab} items={items} /></div>

      {tab === "analytics" && isTop && <AnalyticsTab />}
      {tab === "approvals" && <ApprovalsTab isOwner={isOwner} />}
      {tab === "employees" && isTop && <EmployeesTab />}
      {tab === "tasks" && isOwner && <TasksTab />}
      {tab === "calendar" && isTop && <CalendarTab />}
    </div>
  );
}

function AnalyticsTab() {
  const { data } = useOne<any>(["analytics", "summary"], "/api/owners/analytics/summary");
  if (!data) return <Card><span className="text-sm text-neutral-500">Загрузка…</span></Card>;
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <StatCard label="Доход" value={<Amount value={data.total.income} kind="income" />} />
      <StatCard label="Расход" value={<Amount value={data.total.expense} kind="expense" />} />
      <StatCard label="Прибыль" value={<Amount value={data.total.profit} />} />
    </div>
  );
}

function ApprovalsTab({ isOwner }: { isOwner: boolean }) {
  const { data } = useList(["approvals"], "/api/owners/approvals");
  const vote = useApiMutation({
    mutationFn: ({ id, decision }: { id: string; decision: string }) => api.post(`/api/owners/approvals/${id}/vote`, { decision }),
    invalidate: [["approvals"]],
    successMsg: "Голос учтён",
  });

  const columns: Column<any>[] = [
    { key: "kind", header: "Тип", render: (r) => r.kind },
    { key: "amount", header: "Сумма", align: "right", render: (r) => (r.amount ? <Amount value={r.amount} /> : "—") },
    { key: "votes", header: "Голоса", render: (r) => `С:${r.sohib ?? "—"} И:${r.iftikhor ?? "—"} Д:${r.dovud ?? "—"}` },
    { key: "result", header: "Итог", render: (r) => <StatusChip status={r.result} /> },
    {
      key: "act", header: "", align: "right",
      render: (r) =>
        isOwner && r.result === "pending" ? (
          <div className="flex justify-end gap-1">
            <Button size="sm" onClick={() => vote.mutate({ id: r.id, decision: "yes" })}>Да</Button>
            <Button size="sm" variant="danger" onClick={() => vote.mutate({ id: r.id, decision: "no" })}>Нет</Button>
          </div>
        ) : null,
    },
  ];

  return <Table columns={columns} rows={(data as any)?.items ?? data ?? []} keyField={(r: any) => r.id} cardTitle={(r) => `${r.kind} · ${r.result}`} empty={<Card><span className="text-sm text-neutral-500">Согласований нет</span></Card>} />;
}

function EmployeesTab() {
  const { data: users } = useList(["users"], "/api/users");
  const userOpts = ((users as any)?.items ?? []).map((u: any) => ({ value: u.id, label: `${u.full_name} (${u.phone})` }));
  return (
    <ResourceList
      queryKey={["employees"]}
      listPath="/api/owners/employees"
      keyField={(r: any) => r.id}
      cardTitle={(r: any) => r.position ?? "Сотрудник"}
      columns={[
        { key: "user_id", header: "Пользователь", render: (r: any) => userOpts.find((u: any) => u.value === r.user_id)?.label ?? r.user_id?.slice(0, 8) },
        { key: "position", header: "Должность" },
        { key: "salary", header: "Оклад", align: "right", render: (r: any) => (r.salary ? <Amount value={r.salary} /> : "—") },
      ]}
      create={{ path: "/api/owners/employees", title: "Приём сотрудника", buttonLabel: "Сотрудник",
        fields: [{ name: "user_id", label: "Пользователь", type: "select", options: userOpts }, { name: "position", label: "Должность" }, { name: "salary", label: "Оклад", type: "number" }] }}
    />
  );
}

function TasksTab() {
  const { data: users } = useList(["users"], "/api/users");
  const userOpts = ((users as any)?.items ?? []).map((u: any) => ({ value: u.id, label: u.full_name }));
  return (
    <ResourceList queryKey={["tasks"]} listPath="/api/owners/tasks" keyField={(r: any) => r.id}
      cardTitle={(r: any) => r.title}
      columns={[
        { key: "title", header: "Задача" },
        { key: "assigned_to", header: "Исполнитель", render: (r: any) => userOpts.find((u: any) => u.value === r.assigned_to)?.label ?? "—" },
        { key: "status", header: "Статус", render: (r: any) => <StatusChip status={r.status} /> },
      ]}
      create={{ path: "/api/owners/tasks", title: "Новая задача", buttonLabel: "Задача",
        fields: [{ name: "assigned_to", label: "Исполнитель", type: "select", options: userOpts }, { name: "title", label: "Заголовок" }] }} />
  );
}

function CalendarTab() {
  return (
    <ResourceList queryKey={["calendar"]} listPath="/api/owners/calendar" keyField={(r: any) => r.id}
      cardTitle={(r: any) => r.title}
      columns={[{ key: "title", header: "Событие" }, { key: "type", header: "Тип" }, { key: "at", header: "Когда" }]}
      create={{ path: "/api/owners/calendar", title: "Новое событие", buttonLabel: "Событие",
        fields: [{ name: "title", label: "Название" }, { name: "type", label: "Тип (встреча/дедлайн)" }, { name: "at", label: "Дата", type: "date" }],
        transform: (v) => ({ ...v, at: v.at ? new Date(v.at).toISOString() : null }) }} />
  );
}
