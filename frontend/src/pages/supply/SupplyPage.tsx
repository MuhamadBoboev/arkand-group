import { useState } from "react";
import { api } from "@/shared/api/client";
import { useApiMutation, useList } from "@/shared/api/hooks";
import { useAuth } from "@/shared/model/auth.store";
import { Amount, Button, Card, Input, Modal, PageTitle, ResourceList, Select, StatusChip, Tabs } from "@/shared/ui";

type Business = { id: string; name: string };

export default function SupplyPage() {
  const { can } = useAuth();
  const { data: biz } = useList<Business>(["businesses"], "/api/businesses");
  const bizOptions = (biz?.items ?? []).map((b) => ({ value: b.id, label: b.name }));
  const [tab, setTab] = useState("requests");

  return (
    <div>
      <PageTitle title="Снабжение" subtitle="Заявки, закупки и оприходование на склад" />
      <div className="mb-4">
        <Tabs
          value={tab}
          onChange={setTab}
          items={[
            { key: "requests", label: "Заявки" },
            { key: "purchases", label: "Закупки" },
            { key: "receive", label: "Оприходование" },
          ]}
        />
      </div>

      {tab === "requests" && (
        <ResourceList
          queryKey={["supply", "requests"]}
          listPath="/api/supply/requests"
          keyField={(r: any) => r.id}
          cardTitle={(r: any) => r.items_json?.map((i: any) => i.name).join(", ") || "Заявка"}
          columns={[
            { key: "items", header: "Позиции", render: (r: any) => (r.items_json ?? []).map((i: any) => `${i.name}${i.qty ? " ×" + i.qty : ""}`).join(", ") },
            { key: "business_id", header: "Бизнес", render: (r: any) => bizOptions.find((b) => b.value === r.business_id)?.label ?? r.business_id },
            { key: "status", header: "Статус", render: (r: any) => <StatusChip status={r.status} /> },
          ]}
          create={
            can("supply_request", "create")
              ? {
                  path: "/api/supply/requests",
                  title: "Новая заявка на закупку",
                  buttonLabel: "Заявка",
                  fields: [
                    { name: "business_id", label: "Чей расход (бизнес)", type: "select", options: bizOptions },
                    { name: "name", label: "Материал" },
                    { name: "qty", label: "Количество", type: "number" },
                  ],
                  transform: (v) => ({ business_id: v.business_id, items: [{ name: v.name, qty: v.qty }] }),
                }
              : undefined
          }
        />
      )}

      {tab === "purchases" && (
        <ResourceList
          queryKey={["supply", "purchases"]}
          listPath="/api/supply/purchases"
          keyField={(r: any) => r.id}
          cardTitle={(r: any) => bizOptions.find((b) => b.value === r.business_id)?.label ?? "Закупка"}
          columns={[
            { key: "business_id", header: "Бизнес", render: (r: any) => bizOptions.find((b) => b.value === r.business_id)?.label ?? r.business_id },
            { key: "amount", header: "Сумма", align: "right", render: (r: any) => <Amount value={r.amount} kind="expense" /> },
            { key: "status", header: "Статус", render: (r: any) => <StatusChip status={r.status} /> },
          ]}
          create={
            can("purchase", "create")
              ? {
                  path: "/api/supply/purchases",
                  title: "Новая закупка",
                  buttonLabel: "Закупка",
                  fields: [
                    { name: "business_id", label: "Бизнес", type: "select", options: bizOptions },
                    { name: "amount", label: "Сумма", type: "number" },
                  ],
                }
              : undefined
          }
        />
      )}

      {tab === "receive" && <ReceiveForm bizOptions={bizOptions} canReceive={can("warehouse", "create")} />}
    </div>
  );
}

function ReceiveForm({ bizOptions, canReceive }: { bizOptions: { value: string; label: string }[]; canReceive: boolean }) {
  const { data: nom } = useList(["nomenclature"], "/api/nomenclature");
  const [open, setOpen] = useState(false);
  const [f, setF] = useState<any>({ business_id: "", nomenclature_id: "", qty: 0, source_business: "" });
  const mut = useApiMutation({
    mutationFn: (b: any) => api.post("/api/supply/receive", b),
    invalidate: [["supply"], ["stock"]],
    successMsg: "Оприходовано на склад",
    onSuccess: () => { setOpen(false); setF({ business_id: "", nomenclature_id: "", qty: 0, source_business: "" }); },
  });

  return (
    <div>
      {canReceive && (
        <div className="mb-3 flex justify-end">
          <Button size="sm" onClick={() => setOpen(true)}>+ Оприходование</Button>
        </div>
      )}
      <Card>
        <p className="text-sm text-neutral-500">
          Оприходование увеличивает остаток склада бизнеса и мгновенно синхронизируется у всех отделов.
          Передача между бизнесами создаёт долг.
        </p>
      </Card>

      <Modal open={open} onClose={() => setOpen(false)} title="Оприходование на склад"
        footer={<Button block loading={mut.isPending} disabled={!f.business_id || !f.nomenclature_id || !(f.qty > 0)} onClick={() => mut.mutate(f)}>Оприходовать</Button>}>
        <div className="flex flex-col gap-3">
          <Select label="Склад бизнеса" value={f.business_id} onChange={(e) => setF((s: any) => ({ ...s, business_id: e.target.value }))} placeholder="—" options={bizOptions} />
          <Select label="Номенклатура" value={f.nomenclature_id} onChange={(e) => setF((s: any) => ({ ...s, nomenclature_id: e.target.value }))} placeholder="—"
            options={(nom?.items ?? []).map((n: any) => ({ value: n.id, label: n.name }))} />
          <Input label="Количество" type="number" inputMode="decimal" min={0} step="any"
            error={f.qty < 0 ? "Количество не может быть отрицательным" : undefined}
            value={f.qty || ""} onChange={(e) => setF((s: any) => ({ ...s, qty: e.target.value === "" ? 0 : Number(e.target.value) }))} />
          <Select label="Источник (для межбизнес-передачи → долг)" value={f.source_business} onChange={(e) => setF((s: any) => ({ ...s, source_business: e.target.value }))} placeholder="— (внешний поставщик)" options={bizOptions} />
        </div>
      </Modal>
    </div>
  );
}
