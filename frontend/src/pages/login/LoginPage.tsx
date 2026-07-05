import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { LuChevronDown, LuUsers } from "react-icons/lu";
import { useAuth } from "@/shared/model/auth.store";
import { Button, Input } from "@/shared/ui";

const schema = z.object({
  phone: z
    .string()
    .min(1, "Введите телефон")
    .regex(/^\+?\d[\d\s()-]{6,20}$/, "Некорректный номер телефона"),
  password: z.string().min(1, "Введите пароль"),
});
type Form = z.infer<typeof schema>;

const DEMO_GROUPS: { dept: string; users: [string, string][] }[] = [
  { dept: "Владельцы", users: [
    ["+992900000001", "Сохиб — главный финансист"],
    ["+992900000002", "Ифтихор — суперадмин"],
    ["+992900000003", "Довуд — проектная компания"],
  ] },
  { dept: "Финансы", users: [
    ["+992900000013", "Главный бухгалтер"],
    ["+992900000010", "Кассир"],
    ["+992900000015", "Директор — приём инкассации"],
  ] },
  { dept: "Снабжение", users: [["+992900000011", "Снабженец"]] },
  { dept: "Заводы", users: [["+992900000014", "Оператор бетонного завода"]] },
  { dept: "Застройщик", users: [
    ["+992900000018", "Прораб"],
    ["+992900000016", "Менеджер по продажам"],
  ] },
  { dept: "Проектная компания", users: [["+992900000017", "Архитектор"]] },
  { dept: "Отдел проверки", users: [["+992900000012", "Ревизор"]] },
];

export default function LoginPage() {
  const { login, loading, error } = useAuth();
  const [showDemo, setShowDemo] = useState(true);
  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<Form>({ resolver: zodResolver(schema), defaultValues: { phone: "", password: "" } });

  const onSubmit = async (data: Form) => {
    try {
      await login(data.phone.trim(), data.password);
    } catch {
      /* ошибка показана через store.error */
    }
  };

  const fill = (phone: string) => {
    setValue("phone", phone);
    setValue("password", "arkand");
  };

  return (
    <div className="grid min-h-screen place-items-center bg-paper px-4 py-10">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center">
          <div className="mb-3 grid h-14 w-14 place-items-center rounded-lg bg-brand text-2xl font-bold tracking-tight text-white shadow-md">
            A
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">ARKAND</h1>
          <p className="mt-1 text-sm text-neutral-500">Финансовая CRM холдинга</p>
        </div>

        <form
          onSubmit={handleSubmit(onSubmit)}
          className="flex flex-col gap-4 rounded-lg border border-neutral-100 bg-white p-6 shadow-sm"
        >
          <div>
            <h2 className="text-base font-semibold text-ink">Вход в систему</h2>
            <p className="mt-0.5 text-xs text-neutral-500">Введите телефон и пароль</p>
          </div>
          <Input label="Телефон" placeholder="+992 900 00 00 00" inputMode="tel" autoComplete="username" error={errors.phone?.message} {...register("phone")} />
          <Input label="Пароль" type="password" autoComplete="current-password" error={errors.password?.message} {...register("password")} />
          {error && <div className="rounded-md bg-status-error/10 px-3 py-2 text-sm text-status-error">{error}</div>}
          <Button type="submit" loading={loading} block>
            Войти
          </Button>
        </form>

        {/* Демо-доступы по отделам */}
        <div className="mt-4 overflow-hidden rounded-lg border border-neutral-100 bg-white shadow-sm">
          <button
            type="button"
            onClick={() => setShowDemo((v) => !v)}
            className="flex w-full items-center justify-between px-4 py-3 text-left"
          >
            <span className="flex items-center gap-2 text-sm font-medium text-ink">
              <LuUsers size={16} className="text-brand" />
              Демо-доступы по ролям
            </span>
            <LuChevronDown size={18} className={`text-neutral-400 transition-transform ${showDemo ? "rotate-180" : ""}`} />
          </button>

          {showDemo && (
            <div className="border-t border-neutral-100 px-2 pb-2">
              <p className="px-2 py-2 text-xs text-neutral-500">
                Пароль для всех: <span className="font-semibold text-ink">arkand</span>. Нажмите на роль, чтобы подставить логин.
              </p>
              <div className="flex flex-col gap-2">
                {DEMO_GROUPS.map((g) => (
                  <div key={g.dept}>
                    <div className="px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-neutral-400">{g.dept}</div>
                    {g.users.map(([phone, label]) => (
                      <button
                        key={phone}
                        type="button"
                        onClick={() => fill(phone)}
                        className="flex w-full items-center justify-between gap-3 rounded-md px-2 py-2 text-left hover:bg-neutral-50"
                      >
                        <span className="text-sm text-ink">{label}</span>
                        <span className="font-num text-xs text-neutral-400">{phone}</span>
                      </button>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <p className="mt-6 text-center text-xs text-neutral-400">ARKAND · webrand.tj · +992 988 64 55 43</p>
      </div>
    </div>
  );
}
