import { useList } from "@/shared/api/hooks";
import { Card, Table, TableSkeleton } from "@/shared/ui";

/** Остаток склада бизнеса (реалтайм §6.3). */
export function StockPanel({ path, businessId }: { path: string; businessId: string }) {
  const { data, isLoading } = useList(["stock", businessId], path);
  if (isLoading) return <TableSkeleton rows={4} />;
  const items = (data as any)?.items ?? (Array.isArray(data) ? data : []);
  return (
    <Table
      columns={[
        { key: "nomenclature_id", header: "Номенклатура", render: (r: any) => r.nomenclature_id?.slice(0, 8) },
        { key: "status", header: "Статус", render: (r: any) => r.status },
        { key: "qty", header: "Остаток", align: "right", render: (r: any) => <span className="font-num tabular-nums">{r.qty}</span> },
      ]}
      rows={items}
      keyField={(r: any) => r.id}
      empty={<Card><span className="text-sm text-neutral-500">Склад пуст</span></Card>}
    />
  );
}
