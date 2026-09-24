import { useTranslation } from "react-i18next";
import { useDocumentTitle } from "@/shared/hooks/useDocumentTitle";
import { useHealth } from "@/features/health/hooks/queries/useHealth";

// Página temporal de la Fase 1: comprueba la conexión frontend ↔ api ↔ db.
export function HealthPage() {
  const { t } = useTranslation();
  useDocumentTitle(t("health.title"));
  const { data, isLoading, isError } = useHealth();

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-6 p-6">
      <div>
        <p className="text-sm text-muted-foreground">{t("app.name")}</p>
        <h1 className="text-2xl font-semibold">{t("health.title")}</h1>
      </div>

      {isLoading && <p className="text-muted-foreground">{t("health.loading")}</p>}

      {isError && <p className="text-destructive">{t("health.error")}</p>}

      {data && (
        <dl className="grid grid-cols-2 gap-y-2 rounded-lg border bg-card p-4 text-sm">
          <dt className="text-muted-foreground">{t("health.api")}</dt>
          <dd className="font-medium">{data.status}</dd>
          <dt className="text-muted-foreground">{t("health.database")}</dt>
          <dd className="font-medium">{data.database}</dd>
          <dt className="text-muted-foreground">{t("health.environment")}</dt>
          <dd className="font-medium">{data.environment}</dd>
        </dl>
      )}
    </main>
  );
}
