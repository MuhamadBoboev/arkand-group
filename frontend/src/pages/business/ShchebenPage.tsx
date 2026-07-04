import { useState } from "react";
import { useList } from "@/shared/api/hooks";
import { useAuth } from "@/shared/model/auth.store";
import { Amount, PageTitle, ResourceList, StatusChip, Tabs } from "@/shared/ui";

const B = "shcheben";

export default function ShchebenPage() {
  const { can } = useAuth();
  const [tab, setTab] = useState("fractions");
  const { data: fractions } = useList(["business", B, "fractions"], `/api/shcheben/fractions?business_id=${B}`);
  const { data: shifts } = useList(["business", B, "shifts"], `/api/shcheben/shifts?business_id=${B}`);
  const fracOpts = ((fractions as any)?.items ?? []).map((f: any) => ({ value: f.id, label: f.name }));
  const shiftOpts = ((shifts as any)?.items ?? []).map((s: any) => ({ value: s.id, label: s.shift_date }));
  const canEdit = can("fraction", "create");

  return (
    <div>
      <PageTitle title="Щебёночный завод" subtitle="Фракции, смены, выпуск, заказы, отгрузка (§9.4)" />
      <div className="mb-4">
        <Tabs value={tab} onChange={setTab} items={[
          { key: "fractions", label: "Фракции" }, { key: "shifts", label: "Смены" }, { key: "outputs", label: "Выпуск" }, { key: "orders", label: "Заказы" },
        ]} />
      </div>

      {tab === "fractions" && (
        <ResourceList queryKey={["business", B, "fractions"]} listPath={`/api/shcheben/fractions?business_id=${B}`} keyField={(r: any) => r.id}
          cardTitle={(r: any) => r.name} columns={[{ key: "name", header: "Фракция" }]}
          create={canEdit ? { path: "/api/shcheben/fractions", title: "Новая фракция", buttonLabel: "Фракция", fields: [{ name: "name", label: "Название (песок/щебень 5-20/…)" }], transform: (v) => ({ ...v, business_id: B }) } : undefined} />
      )}

      {tab === "shifts" && (
        <ResourceList queryKey={["business", B, "shifts"]} listPath={`/api/shcheben/shifts?business_id=${B}`} keyField={(r: any) => r.id}
          columns={[{ key: "shift_date", header: "Дата смены" }, { key: "note", header: "Примечание" }]}
          create={canEdit ? { path: "/api/shcheben/shifts", title: "Новая смена", buttonLabel: "Смена", fields: [{ name: "note", label: "Примечание" }], transform: (v) => ({ ...v, business_id: B }) } : undefined} />
      )}

      {tab === "outputs" && (
        <ResourceList queryKey={["business", B, "outputs"]} listPath="/api/shcheben/outputs" keyField={(r: any) => r.id}
          columns={[
            { key: "fraction_id", header: "Фракция", render: (r: any) => fracOpts.find((f: any) => f.value === r.fraction_id)?.label ?? "—" },
            { key: "qty", header: "Выпуск", align: "right", render: (r: any) => <span className="font-num tabular-nums">{r.qty}</span> },
          ]}
          create={canEdit ? { path: "/api/shcheben/outputs", title: "Выпуск по фракции", buttonLabel: "Выпуск",
            fields: [{ name: "shift_id", label: "Смена", type: "select", options: shiftOpts }, { name: "fraction_id", label: "Фракция", type: "select", options: fracOpts }, { name: "qty", label: "Количество", type: "number" }] } : undefined} />
      )}

      {tab === "orders" && (
        <ResourceList queryKey={["orders", B]} listPath="/api/shcheben/orders" keyField={(r: any) => r.id}
          cardTitle={(r: any) => r.mark ?? "Заказ"}
          columns={[{ key: "mark", header: "Фракция" }, { key: "volume", header: "Объём", align: "right" }, { key: "amount", header: "Сумма", align: "right", render: (r: any) => <Amount value={r.amount ?? 0} /> }, { key: "status", header: "Статус", render: (r: any) => <StatusChip status={r.status} /> }]}
          create={can("order", "create") ? { path: "/api/shcheben/orders", title: "Новый заказ щебня", buttonLabel: "Заказ", fields: [{ name: "mark", label: "Фракция" }, { name: "volume", label: "Объём", type: "number" }, { name: "amount", label: "Сумма", type: "number" }] } : undefined} />
      )}
    </div>
  );
}
