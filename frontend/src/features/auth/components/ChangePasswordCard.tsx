import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { ApiError } from "@/shared/lib/apiClient";
import { errorMessageKey, errorMessageParams } from "@/shared/lib/errors";
import { FormInput } from "@/shared/components/form";
import { Button } from "@/shared/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { useMeta } from "@/features/meta/hooks/queries/useMeta";
import { changePasswordSchema, type ChangePasswordFormValues } from "../schemas/auth.schema";
import { useChangePassword } from "../hooks/mutations/useChangePassword";
import { useSendPasswordResetEmail } from "../hooks/mutations/useSendPasswordResetEmail";

const EMPTY: ChangePasswordFormValues = {
  currentPassword: "",
  newPassword: "",
  confirmPassword: "",
};

/**
 * Cambiar la contraseña con la actual (issue #2, decisión 0024): pedirla protege de
 * una sesión abierta en manos de otro y funciona también sin correo. Con correo,
 * quien la haya olvidado sigue teniendo el enlace de recuperación (RF-03).
 */
export function ChangePasswordCard({ email }: { email: string }) {
  const { t } = useTranslation();
  const { data: meta } = useMeta();
  const changePassword = useChangePassword();
  const form = useForm<ChangePasswordFormValues>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: EMPTY,
  });

  const onSubmit = ({ currentPassword, newPassword }: ChangePasswordFormValues) =>
    changePassword.mutate(
      { current: currentPassword, next: newPassword },
      {
        onSuccess: () => {
          form.reset(EMPTY);
          toast.success(t("account.password.changed"));
        },
        onError: (error) => {
          if (error instanceof ApiError && error.code === "wrong_current_password") {
            form.setError("currentPassword", { message: "account.password.wrongCurrent" });
          } else if (error instanceof ApiError && error.code === "password_policy") {
            form.setError("newPassword", { message: "auth.errors.passwordPolicy" });
          } else {
            toast.error(t(errorMessageKey(error), errorMessageParams(error)));
          }
        },
      },
    );

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("account.password.title")}</CardTitle>
        <CardDescription>{t("account.password.description")}</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-6">
        <form onSubmit={form.handleSubmit(onSubmit)} className="grid max-w-md gap-4" noValidate>
          <FormInput
            form={form}
            name="currentPassword"
            type="password"
            label={t("account.password.current")}
            autoComplete="current-password"
          />
          <FormInput
            form={form}
            name="newPassword"
            type="password"
            label={t("account.password.new")}
            autoComplete="new-password"
          />
          <FormInput
            form={form}
            name="confirmPassword"
            type="password"
            label={t("account.password.confirm")}
            autoComplete="new-password"
          />
          <div>
            <Button type="submit" disabled={changePassword.isPending}>
              {t("account.password.submit")}
            </Button>
          </div>
        </form>
        {meta?.email_enabled === true && <ForgottenPassword email={email} />}
      </CardContent>
    </Card>
  );
}

/** Para quien no recuerda la actual: el enlace de recuperación a su correo. */
function ForgottenPassword({ email }: { email: string }) {
  const { t } = useTranslation();
  const sendResetEmail = useSendPasswordResetEmail();
  const [sent, setSent] = useState(false);

  const send = () =>
    sendResetEmail.mutate(email, {
      onSuccess: (result) => {
        if (result === "ok") setSent(true);
        else toast.error(t("auth.errors.generic"));
      },
      onError: (error) => toast.error(t(errorMessageKey(error), errorMessageParams(error))),
    });

  return (
    <div className="grid gap-2 border-t pt-5">
      <p className="text-sm font-medium">{t("account.password.forgotten")}</p>
      {sent ? (
        <p role="status" className="text-sm leading-relaxed text-muted-foreground">
          {t("account.password.sent", { email })}
        </p>
      ) : (
        <>
          <p className="text-sm text-muted-foreground">
            {t("account.password.forgottenHint", { email })}
          </p>
          <div>
            <Button variant="outline" onClick={send} disabled={sendResetEmail.isPending}>
              {t("account.password.send")}
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
