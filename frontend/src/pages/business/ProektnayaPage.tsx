import { useState } from "react";
import { useList } from "@/shared/api/hooks";
import { useAuth } from "@/shared/model/auth.store";
import { Amount, PageTitle, ResourceList, StatusChip, Tabs } from "@/shared/ui";

export default function ProektnayaPage() {
  const { can } = useAuth();
  const [tab, setTab] = useState("clients");
  const { data: clients } = useList(["proektnaya", "clients"], "/api/proektnaya/clients");
  const clientOpts = ((clients as any)?.items ?? []).map((c: any) => ({ value: c.id, label: c.full_name }));
  const canEdit = can("project", "create");

  return (
    <div>
      <PageTitle title="Проектная компания" subtitle="Клиенты, договоры, проекты и авторский надзор" />
      <div className="mb-4">
        <Tabs value={tab} onChange={setTab} items={[
          { key: "clients", label: "Клиенты" }, { key: "contracts", label: "Договоры" },
          { key: "projects", label: "Проекты" }, { key: "supervision", label: "Надзор" },
        ]} />
      </div>

      {tab === "clients" && (
        <ResourceList queryKey={["proektnaya", "clients"]} listPath="/api/proektnaya/clients" keyField={(r: any) => r.id}
          cardTitle={(r: any) => r.full_name}
          columns={[{ key: "full_name", header: "Клиент" }, { key: "phone", header: "Телефон" }, { key: "registered", header: "Регистрация", render: (r: any) => (r.registered ? "да" : "нет") }]}
          create={canEdit ? { path: "/api/proektnaya/clients", title: "Новый клиент", buttonLabel: "Клиент", fields: [{ name: "full_name", label: "ФИО" }, { name: "phone", label: "Телефон" }] } : undefined} />
      )}

      {tab === "contracts" && (
        <ResourceList queryKey={["proektnaya", "contracts"]} listPath="/api/proektnaya/contracts" keyField={(r: any) => r.id}
          columns={[
            { key: "client_id", header: "Клиент", render: (r: any) => clientOpts.find((c: any) => c.value === r.client_id)?.label ?? "—" },
            { key: "amount", header: "Сумма", align: "right", render: (r: any) => <Amount value={r.amount} /> },
            { key: "status", header: "Статус", render: (r: any) => <StatusChip status={r.status} /> },
          ]}
          create={canEdit ? { path: "/api/proektnaya/contracts", title: "Новый договор (график 50/30/20)", buttonLabel: "Договор",
            fields: [{ name: "client_id", label: "Клиент", type: "select", options: clientOpts }, { name: "amount", label: "Сумма", type: "number" }],
            transform: (v) => ({ ...v, schedule_json: { advance: 50, mid: 30, final: 20 } }) } : undefined} />
      )}

      {tab === "projects" && (
        <ResourceList queryKey={["proektnaya", "projects"]} listPath="/api/proektnaya/projects" keyField={(r: any) => r.id}
          cardTitle={(r: any) => r.title}
          columns={[{ key: "title", header: "Проект" }, { key: "status", header: "Статус", render: (r: any) => <StatusChip status={r.status} /> }]}
          create={canEdit ? { path: "/api/proektnaya/projects", title: "Новый проект", buttonLabel: "Проект", fields: [{ name: "title", label: "Название" }] } : undefined} />
      )}

      {tab === "supervision" && (
        <ResourceList queryKey={["proektnaya", "supervision"]} listPath="/api/proektnaya/supervision" keyField={(r: any) => r.id}
          cardTitle={(r: any) => r.name}
          columns={[{ key: "name", header: "Объект надзора" }, { key: "monthly_fee", header: "Оплата/мес", align: "right", render: (r: any) => <Amount value={r.monthly_fee ?? 0} /> }]}
          create={canEdit ? { path: "/api/proektnaya/supervision", title: "Объект авторского надзора", buttonLabel: "Объект надзора", fields: [{ name: "name", label: "Название" }, { name: "monthly_fee", label: "Оплата в месяц", type: "number" }] } : undefined} />
      )}
    </div>
  );
}
