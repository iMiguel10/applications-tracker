import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";

import { useDocumentTitle } from "@/shared/hooks/useDocumentTitle";
import { AuthLayout } from "@/shared/components/layout/AuthLayout";
import { buttonVariants } from "@/shared/components/ui/button";
import { useVerifyEmail } from "@/features/auth/hooks/mutations/useVerifyEmail";

/** Destino del enlace del email de verificación. Funciona con o sin sesión: el
 * enlace puede abrirse en otro dispositivo. */
export function VerifyEmailPage() {
  const { t } = useTranslation();
  useDocumentTitle(t("auth.verifyEmail.title"));
  const [searchParams] = useSearchParams();
  const hasToken = Boolean(searchParams.get("token"));
  const verify = useVerifyEmail();
  const started = useRef(false);

  // Una sola vez: el token sirve una vez, y en desarrollo React monta dos veces
  // los efectos (StrictMode); la segunda llamada daría "enlace no válido".
  useEffect(() => {
    if (!hasToken || started.current) return;
    started.current = true;
    verify.mutate();
  }, [hasToken, verify]);

  const result = hasToken ? verify.data : "invalid_link";
  const message =
    result === "ok"
      ? t("auth.verifyEmail.success")
      : result === "invalid_link"
        ? t("auth.verifyEmail.invalidLink")
        : result === "error" || verify.isError
          ? t("auth.errors.generic")
          : t("auth.verifyEmail.verifying");

  return (
    <AuthLayout
      title={t("auth.verifyEmail.title")}
      subtitle={t("auth.verifyEmail.subtitle")}
      footer={
        <p className="text-sm text-muted-foreground">
          <Link
            to="/login"
            className="font-medium text-primary underline-offset-4 hover:underline"
          >
            {t("auth.forgotPassword.backToLogin")}
          </Link>
        </p>
      }
    >
      <div className="grid gap-4">
        <p
          role={result === undefined || result === "ok" ? "status" : "alert"}
          className="text-sm leading-relaxed"
        >
          {message}
        </p>
        {result !== undefined && (
          // Sin sesión, la ruta protegida manda antes al login.
          <Link to="/dashboard" className={buttonVariants()}>
            {t("auth.verifyEmail.goToApp")}
          </Link>
        )}
      </div>
    </AuthLayout>
  );
}
