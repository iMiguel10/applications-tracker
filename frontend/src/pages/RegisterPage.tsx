import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { RegisterForm } from "@/features/auth/components/RegisterForm";

export function RegisterPage() {
  const { t } = useTranslation();

  return (
    <main className="mx-auto grid min-h-screen max-w-sm content-center gap-6 p-6">
      <div>
        <p className="text-sm text-muted-foreground">{t("app.name")}</p>
        <h1 className="text-2xl font-semibold">{t("auth.signUpTitle")}</h1>
      </div>
      <RegisterForm />
      <p className="text-sm text-muted-foreground">
        {t("auth.haveAccount")}{" "}
        <Link to="/login" className="font-medium text-foreground underline">
          {t("auth.signIn")}
        </Link>
      </p>
    </main>
  );
}
