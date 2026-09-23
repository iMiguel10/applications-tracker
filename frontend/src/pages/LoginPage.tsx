import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { AuthLayout } from "@/shared/components/layout/AuthLayout";
import { LoginForm } from "@/features/auth/components/LoginForm";

export function LoginPage() {
  const { t } = useTranslation();

  return (
    <AuthLayout
      title={t("auth.signInTitle")}
      footer={
        <p className="text-sm text-muted-foreground">
          {t("auth.noAccount")}{" "}
          <Link to="/register" className="font-medium text-foreground underline">
            {t("auth.signUp")}
          </Link>
        </p>
      }
    >
      <LoginForm />
    </AuthLayout>
  );
}
