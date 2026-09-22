import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { LoginForm } from "@/features/auth/components/LoginForm";

export function LoginPage() {
  const { t } = useTranslation();

  return (
    <main className="mx-auto grid min-h-screen max-w-sm content-center gap-6 p-6">
      <div>
        <p className="text-sm text-muted-foreground">{t("app.name")}</p>
        <h1 className="text-2xl font-semibold">{t("auth.signInTitle")}</h1>
      </div>
      <LoginForm />
      <p className="text-sm text-muted-foreground">
        {t("auth.noAccount")}{" "}
        <Link to="/register" className="font-medium text-foreground underline">
          {t("auth.signUp")}
        </Link>
      </p>
    </main>
  );
}
