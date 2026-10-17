import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useDocumentTitle } from "@/shared/hooks/useDocumentTitle";
import { AuthLayout } from "@/shared/components/layout/AuthLayout";
import { RegisterForm } from "@/features/auth/components/RegisterForm";
import { useMeta } from "@/features/meta/hooks/queries/useMeta";

export function RegisterPage() {
  const { t } = useTranslation();
  const { data: meta } = useMeta();
  // Registro cerrado (decisión 0022): se explica en lugar del formulario.
  const closed = meta?.signup_enabled === false;
  const title = closed ? t("auth.signupClosed.title") : t("auth.signUpTitle");
  useDocumentTitle(title);

  return (
    <AuthLayout
      title={title}
      subtitle={closed ? t("auth.signupClosed.description") : t("auth.signUpSubtitle")}
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
      {!closed && <RegisterForm />}
    </AuthLayout>
  );
}
