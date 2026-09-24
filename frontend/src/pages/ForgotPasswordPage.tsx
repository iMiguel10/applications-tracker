import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useDocumentTitle } from "@/shared/hooks/useDocumentTitle";
import { AuthLayout } from "@/shared/components/layout/AuthLayout";
import { ForgotPasswordForm } from "@/features/auth/components/ForgotPasswordForm";
import { useMeta } from "@/features/meta/hooks/queries/useMeta";

export function ForgotPasswordPage() {
  const { t } = useTranslation();
  useDocumentTitle(t("auth.forgotPassword.title"));
  const meta = useMeta();

  return (
    <AuthLayout
      title={t("auth.forgotPassword.title")}
      subtitle={t("auth.forgotPassword.subtitle")}
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
      {/* Solo se oculta con la certeza de que no hay correo: si /meta falla, el
          formulario sigue ahí y el backend responde igual. */}
      {meta.data?.email_enabled === false ? (
        <p role="status" className="text-sm leading-relaxed">
          {t("auth.forgotPassword.unavailable")}
        </p>
      ) : (
        <ForgotPasswordForm />
      )}
    </AuthLayout>
  );
}
