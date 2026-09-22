import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { registerSchema, type RegisterFormValues } from "../schemas/auth.schema";
import { useSignUp } from "../hooks/mutations/useSignUp";

// Los FIELD_ERROR de SuperTokens llegan en inglés: se traducen por campo. La regla
// la aplica el backend; aquí solo se explica.
const FIELD_ERROR_KEYS = {
  email: "auth.errors.emailRejected",
  password: "auth.errors.passwordPolicy",
} as const;

export function RegisterForm() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const signUp = useSignUp();

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { email: "", password: "", confirmPassword: "" },
  });

  const onSubmit = ({ email, password }: RegisterFormValues) =>
    signUp.mutate(
      { email, password },
      {
        onSuccess: (result) => {
          if (result.status === "ok") {
            navigate("/applications", { replace: true });
          } else if (result.status === "field_errors") {
            for (const field of result.fields) {
              setError(field, { message: FIELD_ERROR_KEYS[field] });
            }
          } else {
            toast.error(t("auth.errors.generic"));
          }
        },
        onError: () => toast.error(t("auth.errors.generic")),
      },
    );

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
          autoComplete="new-password"
          aria-invalid={!!errors.password}
          {...register("password")}
        />
        {errors.password?.message && (
          <p className="text-sm text-destructive">{t(errors.password.message)}</p>
        )}
      </div>

      <div className="grid gap-2">
        <Label htmlFor="confirmPassword">{t("auth.fields.confirmPassword")}</Label>
        <Input
          id="confirmPassword"
          type="password"
          autoComplete="new-password"
          aria-invalid={!!errors.confirmPassword}
          {...register("confirmPassword")}
        />
        {errors.confirmPassword?.message && (
          <p className="text-sm text-destructive">{t(errors.confirmPassword.message)}</p>
        )}
      </div>

      <Button type="submit" disabled={signUp.isPending}>
        {t("auth.signUp")}
      </Button>
    </form>
  );
}
