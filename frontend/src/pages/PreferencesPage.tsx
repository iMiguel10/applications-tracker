import { useTranslation } from "react-i18next";

import { PreferencesForm } from "@/features/auth/components/PreferencesForm";
import { usePreferences } from "@/features/auth/hooks/queries/usePreferences";

export function PreferencesPage() {
  const { t } = useTranslation();
  const { data, isLoading, isError } = usePreferences();

  return (
    <div className="grid gap-6">
      <h1 className="text-2xl font-semibold">{t("preferences.title")}</h1>

      {isLoading && <p className="text-muted-foreground">{t("common.loading")}</p>}
      {isError && <p className="text-destructive">{t("errors.generic")}</p>}
      {data && <PreferencesForm preferences={data} />}
    </div>
  );
}
