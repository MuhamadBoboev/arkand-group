import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useAuth } from "@/shared/model/auth.store";
import { Button, Input } from "@/shared/ui";

const schema = z.object({
  phone: z.string().min(3, "Введите телефон"),
  password: z.string().min(1, "Введите пароль"),
});
type Form = z.infer<typeof schema>;

const DEMO = [
  ["+992900000001", "Сохиб — гл. финансист"],
  ["+992900000002", "Ифтихор — суперадмин"],
  ["+992900000003", "Довуд — проектная"],
  ["+992900000010", "Кассир"],
  ["+992900000012", "Ревизор"],
  ["+992900000014", "Оператор завода"],
];

export default function LoginPage() {
  const { login, loading, error } = useAuth();
  const { register, handleSubmit, setValue, formState: { errors } } = useForm<Form>({
    resolver: zodResolver(schema),
    defaultValues: { phone: "", password: "arkand" },
  });

  const onSubmit = async (data: Form) => {
    try {
      await login(data.phone, data.password);
    } catch {
      /* ошибка показана через store.error */
    }
  };

  return (
    <div className="grid min-h-screen place-items-center bg-paper px-4 py-8">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 grid h-14 w-14 place-items-center rounded-lg bg-brand text-2xl font-bold text-white">A</div>
          <h1 className="text-2xl font-bold text-ink">ARKAND</h1>
          <p className="text-sm text-neutral-500">Финансовая CRM холдинга</p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4 rounded-lg border border-neutral-100 bg-white p-5 shadow-sm">
          <Input label="Телефон" placeholder="+992900000001" inputMode="tel" autoComplete="username" error={errors.phone?.message} {...register("phone")} />
          <Input label="Пароль" type="password" autoComplete="current-password" error={errors.password?.message} {...register("password")} />
          {error && <div className="rounded-md bg-status-error/10 px-3 py-2 text-sm text-status-error">{error}</div>}
          <Button type="submit" loading={loading} block>
            Войти
          </Button>
        </form>

        <div className="mt-4 rounded-lg border border-dashed border-neutral-200 p-3">
          <p className="mb-2 text-xs font-medium text-neutral-500">Демо-доступы (пароль: arkand)</p>
          <div className="flex flex-col gap-1">
            {DEMO.map(([phone, label]) => (
              <button
                key={phone}
                onClick={() => { setValue("phone", phone); setValue("password", "arkand"); }}
                className="flex items-center justify-between rounded-md px-2 py-1.5 text-left text-xs hover:bg-neutral-100"
              >
                <span className="text-neutral-600">{label}</span>
                <span className="font-num text-neutral-400">{phone}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
