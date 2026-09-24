import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";

import { Button, buttonVariants } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { resetPasswordSchema, type ResetPasswordFormValues } from "../schemas/auth.schema";
import { useSubmitNewPassword } from "../hooks/mutations/useSubmitNewPassword";

export function ResetPasswordForm() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  // Sin token en la URL no hay nada que intentar: se dice ya, sin rellenar nada.
  const [invalidLink, setInvalidLink] = useState(!searchParams.get("token"));
  const submitNewPassword = useSubmitNewPassword();

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<ResetPasswordFormValues>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { password: "", confirmPassword: "" },
  });

  const onSubmit = ({ password }: ResetPasswordFormValues) =>
    submitNewPassword.mutate(password, {
      onSuccess: (result) => {
        if (result.status === "ok") {
          toast.success(t("auth.resetPassword.success"));
          navigate("/login", { replace: true });
        } else if (result.status === "invalid_link") {
          setInvalidLink(true);
        } else if (result.status === "password_policy") {
          setError("password", { message: "auth.errors.passwordPolicy" });
        } else {
          toast.error(t("auth.errors.generic"));
        }
      },
      onError: () => toast.error(t("auth.errors.generic")),
    });

  if (invalidLink) {
    return (
      <div className="grid gap-4">
        <p role="alert" className="text-sm leading-relaxed">
          {t("auth.resetPassword.invalidLink")}
        </p>
        <Link to="/forgot-password" className={buttonVariants()}>
          {t("auth.resetPassword.requestNew")}
        </Link>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="grid gap-4" noValidate>
      <div className="grid gap-2">
        <Label htmlFor="password">{t("auth.fields.newPassword")}</Label>
        <Input
          id="password"
          type="password"
          autoComplete="new-password"
          aria-invalid={!!errors.password}
          aria-describedby={errors.password ? "password-error" : undefined}
          {...register("password")}
        />
        {errors.password?.message && (
          <p id="password-error" className="text-sm text-destructive">{t(errors.password.message)}</p>
        )}
      </div>

      <div className="grid gap-2">
        <Label htmlFor="confirmPassword">{t("auth.fields.confirmPassword")}</Label>
        <Input
          id="confirmPassword"
          type="password"
          autoComplete="new-password"
          aria-invalid={!!errors.confirmPassword}
          aria-describedby={errors.confirmPassword ? "confirmPassword-error" : undefined}
          {...register("confirmPassword")}
        />
        {errors.confirmPassword?.message && (
          <p id="confirmPassword-error" className="text-sm text-destructive">{t(errors.confirmPassword.message)}</p>
        )}
      </div>

      <Button type="submit" disabled={submitNewPassword.isPending}>
        {t("auth.resetPassword.submit")}
      </Button>
    </form>
  );
}
