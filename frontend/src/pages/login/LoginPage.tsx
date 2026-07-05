import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
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

export default function LoginPage() {
  const { login, loading, error } = useAuth();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<Form>({ resolver: zodResolver(schema), defaultValues: { phone: "", password: "" } });

  const onSubmit = async (data: Form) => {
    try {
      await login(data.phone.trim(), data.password);
    } catch {
      /* ошибка показана через store.error */
    }
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
          <Input
            label="Телефон"
            placeholder="+992 900 00 00 00"
            inputMode="tel"
            autoComplete="username"
            error={errors.phone?.message}
            {...register("phone")}
          />
          <Input
            label="Пароль"
            type="password"
            autoComplete="current-password"
            error={errors.password?.message}
            {...register("password")}
          />
          {error && (
            <div className="rounded-md bg-status-error/10 px-3 py-2 text-sm text-status-error">{error}</div>
          )}
          <Button type="submit" loading={loading} block>
            Войти
          </Button>
        </form>

        <p className="mt-6 text-center text-xs text-neutral-400">
          ARKAND · webrand.tj · +992 988 64 55 43
        </p>
      </div>
    </div>
  );
}
