import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useDocumentTitle } from "@/shared/hooks/useDocumentTitle";
import { AuthLayout } from "@/shared/components/layout/AuthLayout";
import { LoginForm } from "@/features/auth/components/LoginForm";
import { useMeta } from "@/features/meta/hooks/queries/useMeta";

export function LoginPage() {
  const { t } = useTranslation();
  useDocumentTitle(t("auth.signInTitle"));
  const { data: meta } = useMeta();
  // Con el registro cerrado (decisión 0022) no se ofrece crear una cuenta.
  const signupClosed = meta?.signup_enabled === false;

  return (
    <AuthLayout
      title={t("auth.signInTitle")}
      subtitle={t("auth.signInSubtitle")}
      footer={
        signupClosed ? undefined : (
          <p className="text-sm text-muted-foreground">
            {t("auth.noAccount")}{" "}
            <Link
              to="/register"
              className="font-medium text-primary underline-offset-4 hover:underline"
            >
              {t("auth.signUp")}
            </Link>
          </p>
        )
      }
    >
      <LoginForm />
    </AuthLayout>
  );
}
