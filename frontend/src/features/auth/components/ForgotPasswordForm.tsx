import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { forgotPasswordSchema, type ForgotPasswordFormValues } from "../schemas/auth.schema";
import { useSendPasswordResetEmail } from "../hooks/mutations/useSendPasswordResetEmail";

export function ForgotPasswordForm() {
  const { t } = useTranslation();
  const sendResetEmail = useSendPasswordResetEmail();
  const [sentTo, setSentTo] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotPasswordFormValues>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: "" },
  });

  const onSubmit = ({ email }: ForgotPasswordFormValues) =>
    sendResetEmail.mutate(email, {
      onSuccess: (result) => {
        if (result === "ok") setSentTo(email);
        else toast.error(t("auth.errors.generic"));
      },
      onError: () => toast.error(t("auth.errors.generic")),
    });

  if (sentTo !== null) {
    // Mismo mensaje exista o no la cuenta: la respuesta del backend no lo dice (T9).
    return (
      <p role="status" className="text-sm leading-relaxed">
        {t("auth.forgotPassword.sent", { email: sentTo })}
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="grid gap-4" noValidate>
      <div className="grid gap-2">
        <Label htmlFor="email">{t("auth.fields.email")}</Label>
        <Input
          id="email"
          type="email"
          autoComplete="email"
          aria-invalid={!!errors.email}
          aria-describedby={errors.email ? "email-error" : undefined}
          {...register("email")}
        />
        {errors.email?.message && (
          <p id="email-error" className="text-sm text-destructive">{t(errors.email.message)}</p>
        )}
      </div>

      <Button type="submit" disabled={sendResetEmail.isPending}>
        {t("auth.forgotPassword.submit")}
      </Button>
    </form>
  );
}
