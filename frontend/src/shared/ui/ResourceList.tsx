import { useState } from "react";
import { api } from "@/shared/api/client";
import { useApiMutation, useList } from "@/shared/api/hooks";
import { Button } from "./Button";
import { Input } from "./Input";
import { Select } from "./Select";
import { Modal } from "./Modal";
import { Table, type Column } from "./Table";
import { TableSkeleton } from "./Skeleton";
import { EmptyState } from "./EmptyState";

export interface Field {
  name: string;
  label: string;
  type?: "text" | "number" | "date" | "select";
  options?: { value: string; label: string }[];
  required?: boolean;
  min?: number;
  placeholder?: string;
}

interface Props<T> {
  queryKey: unknown[];
  listPath: string;
  columns: Column<T>[];
  keyField: (row: T) => string;
  cardTitle?: (row: T) => React.ReactNode;
  create?: {
    path: string;
    fields: Field[];
    title: string;
    transform?: (v: Record<string, any>) => any;
    buttonLabel?: string;
  };
  emptyTitle?: string;
}

/** Универсальный список сущности модуля: таблица→карточки + модалка создания. */
export function ResourceList<T>({ queryKey, listPath, columns, keyField, cardTitle, create, emptyTitle }: Props<T>) {
  const { data, isLoading } = useList<T>(queryKey, listPath);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<Record<string, any>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});

  const mut = useApiMutation({
    mutationFn: (body: any) => api.post(create!.path, body),
    invalidate: [queryKey],
    successMsg: "Создано",
    onSuccess: () => { setOpen(false); setForm({}); setErrors({}); },
  });

  const validate = (): boolean => {
    const e: Record<string, string> = {};
    for (const f of create?.fields ?? []) {
      const v = form[f.name];
      const empty = v === undefined || v === null || v === "";
      if (f.required !== false && empty) {
        e[f.name] = "Обязательное поле";
        continue;
      }
      if (f.type === "number" && !empty) {
        const n = Number(v);
        if (!Number.isFinite(n)) e[f.name] = "Введите число";
        else if (n < 0) e[f.name] = "Число не может быть отрицательным";
        else if (n === 0 && f.required !== false) e[f.name] = "Введите значение больше 0";
        else if (f.min !== undefined && n < f.min) e[f.name] = `Минимум ${f.min}`;
      }
    }
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const submit = () => {
    if (!validate()) return;
    const body = create?.transform ? create.transform(form) : form;
    mut.mutate(body);
  };

  return (
    <div>
      {create && (
        <div className="mb-3 flex justify-end">
          <Button size="sm" onClick={() => setOpen(true)}>+ {create.buttonLabel ?? "Добавить"}</Button>
        </div>
      )}

      {isLoading ? (
        <TableSkeleton />
      ) : (
        <Table
          columns={columns}
          rows={data?.items ?? []}
          keyField={keyField}
          cardTitle={cardTitle}
          empty={<EmptyState title={emptyTitle ?? "Пока пусто"} />}
        />
      )}

      {create && (
        <Modal
          open={open}
          onClose={() => setOpen(false)}
          title={create.title}
          footer={
            <Button block loading={mut.isPending} onClick={submit}>
              Сохранить
            </Button>
          }
        >
          <div className="flex flex-col gap-3">
            {create.fields.map((f) =>
              f.type === "select" ? (
                <Select
                  key={f.name}
                  label={f.label}
                  placeholder={f.placeholder ?? "—"}
                  options={f.options ?? []}
                  error={errors[f.name]}
                  value={form[f.name] ?? ""}
                  onChange={(e) => setForm((s) => ({ ...s, [f.name]: e.target.value }))}
                />
              ) : (
                <Input
                  key={f.name}
                  label={f.label}
                  type={f.type === "number" ? "number" : f.type === "date" ? "date" : "text"}
                  inputMode={f.type === "number" ? "decimal" : undefined}
                  step={f.type === "number" ? "any" : undefined}
                  min={f.type === "number" ? 0 : undefined}
                  placeholder={f.placeholder}
                  error={errors[f.name]}
                  value={form[f.name] ?? ""}
                  onChange={(e) => {
                    const raw = e.target.value;
                    setForm((s) => ({ ...s, [f.name]: f.type === "number" ? (raw === "" ? "" : Number(raw)) : raw }));
                  }}
                />
              ),
            )}
          </div>
        </Modal>
      )}
    </div>
  );
}
