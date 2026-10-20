import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { errorMessageKey, errorMessageParams } from "@/shared/lib/errors";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { LegalConsent } from "@/features/legal/components/LegalConsent";
import { useMeta } from "@/features/meta/hooks/queries/useMeta";
import { registerSchema, type RegisterFormValues } from "../schemas/auth.schema";
import { useAcceptLegal } from "../hooks/mutations/useAcceptLegal";
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
  const acceptLegal = useAcceptLegal();
  const { data: meta } = useMeta();
  // Con textos legales (issue #3), hay que aceptarlos para crear la cuenta.
  const legal = meta?.legal.configured ? meta.legal : null;
  const [legalAccepted, setLegalAccepted] = useState(false);
  const [legalMissing, setLegalMissing] = useState(false);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { email: "", password: "", confirmPassword: "" },
  });

  const onSubmit = ({ email, password }: RegisterFormValues) => {
    if (legal && !legalAccepted) {
      setLegalMissing(true);
      return;
    }
    signUp.mutate(
      { email, password },
      {
        onSuccess: async (result) => {
          if (result.status === "ok") {
            // Si no se pudiera registrar ahora, la pantalla de aceptación lo pide al
            // entrar: la cuenta no se queda sin aceptar.
            if (legal) await acceptLegal.mutateAsync(legal.version).catch(() => undefined);
            navigate("/applications", { replace: true });
          } else if (result.status === "field_errors") {
            for (const field of result.fields) {
              setError(field, { message: FIELD_ERROR_KEYS[field] });
            }
          } else if (result.status === "signup_disabled") {
            // Se cerró con la página ya abierta.
            toast.error(t("auth.signupClosed.description"));
          } else {
            toast.error(t("auth.errors.generic"));
          }
        },
        onError: (error) => toast.error(t(errorMessageKey(error), errorMessageParams(error))),
      },
    );
  };

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

      <div className="grid gap-2">
        <Label htmlFor="password">{t("auth.fields.password")}</Label>
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

      {legal && (
        <div className="grid gap-2">
          <LegalConsent
            checked={legalAccepted}
            onChange={(value) => {
              setLegalAccepted(value);
              if (value) setLegalMissing(false);
            }}
            errorId={legalMissing ? "legal-consent-error" : undefined}
          />
          {legalMissing && (
            <p id="legal-consent-error" className="text-sm text-destructive">
              {t("legal.consent.required")}
            </p>
          )}
        </div>
      )}

      <Button type="submit" disabled={signUp.isPending || acceptLegal.isPending}>
        {t("auth.signUp")}
      </Button>
    </form>
  );
}
