import { useState } from "react";
import { useList } from "@/shared/api/hooks";
import { useAuth } from "@/shared/model/auth.store";
import { Amount, PageTitle, ResourceList, StatusChip, Tabs } from "@/shared/ui";
import { StockPanel } from "./StockPanel";

const B = "beton";

export default function BetonPage() {
  const { can } = useAuth();
  const [tab, setTab] = useState("orders");
  const { data: recipes } = useList(["business", B, "recipes"], "/api/beton/recipes");
  const markOpts = ((recipes as any)?.items ?? []).map((r: any) => ({ value: r.mark, label: r.mark }));

  return (
    <div>
      <PageTitle title="Бетонный завод" subtitle="Заказы, рецептуры, отгрузка и контроль качества" />
      <div className="mb-4">
        <Tabs value={tab} onChange={setTab} items={[
          { key: "orders", label: "Заказы" }, { key: "recipes", label: "Рецептуры" }, { key: "shipping", label: "Отгрузка" }, { key: "stock", label: "Склад" },
        ]} />
      </div>

      {tab === "orders" && (
        <ResourceList queryKey={["orders", B]} listPath="/api/beton/orders" keyField={(r: any) => r.id}
          cardTitle={(r: any) => `Бетон ${r.mark ?? ""}`}
          columns={[
            { key: "mark", header: "Марка" },
            { key: "volume", header: "Объём, м³", align: "right" },
            { key: "amount", header: "Сумма", align: "right", render: (r: any) => <Amount value={r.amount ?? 0} /> },
            { key: "status", header: "Статус", render: (r: any) => <StatusChip status={r.status} /> },
          ]}
          create={can("order", "create") ? {
            path: "/api/beton/orders", title: "Новый заказ бетона", buttonLabel: "Заказ",
            fields: [
              { name: "mark", label: "Марка", type: "select", options: markOpts.length ? markOpts : [{ value: "M300", label: "M300" }] },
              { name: "volume", label: "Объём, м³", type: "number" },
              { name: "amount", label: "Сумма", type: "number" },
            ],
          } : undefined} />
      )}

      {tab === "recipes" && (
        <ResourceList queryKey={["business", B, "recipes"]} listPath="/api/beton/recipes" keyField={(r: any) => r.id}
          cardTitle={(r: any) => r.mark}
          columns={[{ key: "mark", header: "Марка" }, { key: "valid_from", header: "Действует с" }]}
          create={can("recipe", "create") ? {
            path: "/api/beton/recipes", title: "Новая рецептура", buttonLabel: "Рецептура",
            fields: [{ name: "mark", label: "Марка бетона" }],
            transform: (v) => ({ business_id: B, mark: v.mark, frozen_json: { components: [] } }),
          } : undefined} />
      )}

      {tab === "shipping" && (
        <ResourceList queryKey={["business", B, "shipping"]} listPath="/api/beton/shipping" keyField={(r: any) => r.id}
          cardTitle={(r: any) => `Талон ${r.vehicle ?? ""}`}
          columns={[{ key: "vehicle", header: "Машина" }, { key: "qty", header: "Кол-во", align: "right" }, { key: "status", header: "Статус", render: (r: any) => <StatusChip status={r.status} /> }]}
          create={can("shipping", "create") ? {
            path: "/api/beton/shipping", title: "Талон отгрузки", buttonLabel: "Отгрузка",
            fields: [{ name: "vehicle", label: "Машина (номер)" }, { name: "qty", label: "Количество, м³", type: "number" }],
          } : undefined} />
      )}

      {tab === "stock" && <StockPanel path="/api/beton/stock" businessId={B} />}
    </div>
  );
}
