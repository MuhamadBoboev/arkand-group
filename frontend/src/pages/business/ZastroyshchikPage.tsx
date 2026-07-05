import { useState } from "react";
import { useList } from "@/shared/api/hooks";
import { useAuth } from "@/shared/model/auth.store";
import { Amount, PageTitle, ResourceList, Tabs } from "@/shared/ui";
import { StockPanel } from "./StockPanel";

const B = "zastroyshchik";

export default function ZastroyshchikPage() {
  const { can } = useAuth();
  const [tab, setTab] = useState("objects");
  const { data: objects } = useList(["business", B, "objects"], `/api/zastroyshchik/objects?business_id=${B}`);

  return (
    <div>
      <PageTitle title="Застройщик" subtitle="Объекты, сметы, склад и прибыль по объектам" />
      <div className="mb-4">
        <Tabs value={tab} onChange={setTab} items={[
          { key: "objects", label: "Объекты" }, { key: "estimates", label: "Сметы" }, { key: "stock", label: "Склад" },
        ]} />
      </div>

      {tab === "objects" && (
        <ResourceList
          queryKey={["business", B, "objects"]}
          listPath={`/api/zastroyshchik/objects?business_id=${B}`}
          keyField={(r: any) => r.id}
          cardTitle={(r: any) => r.name}
          columns={[
            { key: "name", header: "Объект" },
            { key: "city", header: "Город" },
            { key: "address", header: "Адрес", hideOnMobile: true },
            { key: "status", header: "Статус" },
          ]}
          create={can("object", "create") ? {
            path: "/api/zastroyshchik/objects", title: "Новый объект", buttonLabel: "Объект",
            fields: [{ name: "name", label: "Название" }, { name: "city", label: "Город" }, { name: "address", label: "Адрес" }],
            transform: (v) => ({ ...v, business_id: B }),
          } : undefined}
        />
      )}

      {tab === "estimates" && (
        <ResourceList
          queryKey={["business", B, "estimates"]}
          listPath="/api/zastroyshchik/estimates"
          keyField={(r: any) => r.id}
          columns={[
            { key: "object_id", header: "Объект", render: (r: any) => (objects as any)?.items?.find((o: any) => o.id === r.object_id)?.name ?? r.object_id?.slice(0, 8) },
            { key: "plan_amount", header: "План", align: "right", render: (r: any) => <Amount value={r.plan_amount ?? 0} /> },
            { key: "fact_amount", header: "Факт", align: "right", render: (r: any) => <Amount value={r.fact_amount ?? 0} kind="expense" /> },
          ]}
          create={can("object", "create") ? {
            path: "/api/zastroyshchik/estimates", title: "Новая смета (замораживается на дату)", buttonLabel: "Смета",
            fields: [
              { name: "object_id", label: "Объект", type: "select", options: ((objects as any)?.items ?? []).map((o: any) => ({ value: o.id, label: o.name })) },
              { name: "plan_amount", label: "План, сумма", type: "number" },
            ],
          } : undefined}
        />
      )}

      {tab === "stock" && <StockPanel path={`/api/zastroyshchik/stock?business_id=${B}`} businessId={B} />}
    </div>
  );
}
