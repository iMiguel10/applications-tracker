import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";

import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { loginSchema, type LoginFormValues } from "../schemas/auth.schema";
import { useSignIn } from "../hooks/mutations/useSignIn";
import { safeRedirect } from "../lib/safeRedirect";

export function LoginForm() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const signIn = useSignIn();

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  const onSubmit = (values: LoginFormValues) =>
    signIn.mutate(values, {
      onSuccess: (result) => {
        if (result.status === "ok") {
          navigate(safeRedirect(searchParams.get("redirect")), { replace: true });
        } else if (result.status === "wrong_credentials") {
          // Mensaje único: no revela si falla el email o la contraseña.
          setError("root", { message: "auth.errors.wrongCredentials" });
        } else {
          toast.error(t("auth.errors.generic"));
        }
      },
      onError: () => toast.error(t("auth.errors.generic")),
    });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="grid gap-4" noValidate>
      <div className="grid gap-2">
        <Label htmlFor="email">{t("auth.fields.email")}</Label>
        <Input
          id="email"
          type="email"
          autoComplete="email"
          aria-invalid={!!errors.email}
          {...register("email")}
        />
        {errors.email?.message && (
          <p className="text-sm text-destructive">{t(errors.email.message)}</p>
        )}
      </div>

      <div className="grid gap-2">
        <Label htmlFor="password">{t("auth.fields.password")}</Label>
        <Input
          id="password"
          type="password"
          autoComplete="current-password"
          aria-invalid={!!errors.password}
          {...register("password")}
        />
        {errors.password?.message && (
          <p className="text-sm text-destructive">{t(errors.password.message)}</p>
        )}
      </div>

      {errors.root?.message && (
        <p role="alert" className="text-sm text-destructive">
          {t(errors.root.message)}
        </p>
      )}

      <Button type="submit" disabled={signIn.isPending}>
        {t("auth.signIn")}
      </Button>
    </form>
  );
}
