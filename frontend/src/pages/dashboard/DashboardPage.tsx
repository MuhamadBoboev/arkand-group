import { useOne, useList } from "@/shared/api/hooks";
import { useAuth } from "@/shared/model/auth.store";
import { Amount, Card, PageTitle, StatCard, Skeleton, StatusChip } from "@/shared/ui";

type Summary = {
  total: { income: string; expense: string; profit: string };
  by_business: { business_id: string; business_name: string; income: string; expense: string; profit: string }[];
};

export default function DashboardPage() {
  const { user, can } = useAuth();
  const isOwnerTop = user?.is_owner && (user.owner_type === "sohib" || user.owner_type === "iftikhor");

  const { data: summary, isLoading } = useOne<Summary>(["analytics", "summary"], "/api/owners/analytics/summary", !!isOwnerTop);
  const { data: tasks } = useList(["tasks"], "/api/owners/tasks");
  const { data: cash } = useList(["finance", "cash"], "/api/finance/cash", can("cash", "view"));

  return (
    <div>
      <PageTitle title={`Здравствуйте, ${user?.full_name?.split(" ")[0] ?? ""}`} subtitle="Сводка по холдингу ARKAND" />

      {isOwnerTop && (
        <section className="mb-6">
          <h2 className="mb-2 text-sm font-semibold text-neutral-500">Консолидация (§9.7)</h2>
          {isLoading ? (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <Skeleton className="h-24" /><Skeleton className="h-24" /><Skeleton className="h-24" />
            </div>
          ) : summary ? (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <StatCard label="Доход" value={<Amount value={summary.total.income} kind="income" />} />
              <StatCard label="Расход" value={<Amount value={summary.total.expense} kind="expense" />} />
              <StatCard label="Прибыль" value={<Amount value={summary.total.profit} />} />
            </div>
          ) : null}

          {summary?.by_business?.length ? (
            <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {summary.by_business.map((b) => (
                <Card key={b.business_id}>
                  <div className="mb-2 font-medium text-ink">{b.business_name}</div>
                  <div className="flex flex-col gap-1 text-sm">
                    <Row label="Доход"><Amount value={b.income} kind="income" /></Row>
                    <Row label="Расход"><Amount value={b.expense} kind="expense" /></Row>
                    <Row label="Прибыль"><Amount value={b.profit} /></Row>
                  </div>
                </Card>
              ))}
            </div>
          ) : null}
        </section>
      )}

      {can("cash", "view") && cash?.items?.length ? (
        <section className="mb-6">
          <h2 className="mb-2 text-sm font-semibold text-neutral-500">Мои кассы</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {cash.items.map((c: any) => (
              <StatCard key={c.id} label={c.name} value={<Amount value={c.balance} />} sub="баланс" />
            ))}
          </div>
        </section>
      ) : null}

      <section>
        <h2 className="mb-2 text-sm font-semibold text-neutral-500">Мои задачи</h2>
        {tasks?.items?.length ? (
          <div className="flex flex-col gap-2">
            {tasks.items.slice(0, 6).map((t: any) => (
              <Card key={t.id} className="flex items-center justify-between gap-3">
                <span className="text-sm text-ink">{t.title}</span>
                <StatusChip status={t.status} />
              </Card>
            ))}
          </div>
        ) : (
          <Card><span className="text-sm text-neutral-500">Задач нет</span></Card>
        )}
      </section>
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-neutral-500">{label}</span>
      {children}
    </div>
  );
}
