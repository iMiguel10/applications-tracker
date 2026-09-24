import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useDocumentTitle } from "@/shared/hooks/useDocumentTitle";
import { AuthLayout } from "@/shared/components/layout/AuthLayout";
import { ResetPasswordForm } from "@/features/auth/components/ResetPasswordForm";

export function ResetPasswordPage() {
  const { t } = useTranslation();
  useDocumentTitle(t("auth.resetPassword.title"));

  return (
    <AuthLayout
      title={t("auth.resetPassword.title")}
      subtitle={t("auth.resetPassword.subtitle")}
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
      <ResetPasswordForm />
    </AuthLayout>
  );
}
