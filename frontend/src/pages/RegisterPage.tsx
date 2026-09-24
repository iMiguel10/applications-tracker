import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useDocumentTitle } from "@/shared/hooks/useDocumentTitle";
import { AuthLayout } from "@/shared/components/layout/AuthLayout";
import { RegisterForm } from "@/features/auth/components/RegisterForm";

export function RegisterPage() {
  const { t } = useTranslation();
  useDocumentTitle(t("auth.signUpTitle"));

  return (
    <AuthLayout
      title={t("auth.signUpTitle")}
      subtitle={t("auth.signUpSubtitle")}
      footer={
        <p className="text-sm text-muted-foreground">
          {t("auth.haveAccount")}{" "}
          <Link
            to="/login"
            className="font-medium text-primary underline-offset-4 hover:underline"
          >
            {t("auth.signIn")}
          </Link>
        </p>
      }
    >
      <RegisterForm />
    </AuthLayout>
  );
}
