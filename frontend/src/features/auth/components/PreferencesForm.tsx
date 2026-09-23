import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Moon, Sun } from "lucide-react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { useTheme } from "@/app/providers/useTheme";
import { errorMessageKey } from "@/shared/lib/errors";
import { FormActions, FormInput, FormSelect } from "@/shared/components/form";
import { Switch } from "@/shared/components/ui/switch";
import { useUpdatePreferences } from "../hooks/mutations/useUpdatePreferences";
import { preferencesSchema, type PreferencesFormValues } from "../schemas/preferences.schema";
import { LANGUAGES, type Preferences } from "../types/Auth";

// Tema claro/oscuro (F8.4): vive en el navegador (ThemeProvider), no en esta
// preferencia de cuenta — por eso no pasa por `useUpdatePreferences`.
function ThemeField() {
  const { t } = useTranslation();
  const { resolvedTheme, setTheme } = useTheme();
  const isDark = resolvedTheme === "dark";

  return (
    <div className="grid gap-2">
      <span className="text-sm font-medium">{t("preferences.fields.theme")}</span>
      <label className="flex w-fit cursor-pointer items-center gap-3">
        <Sun className="size-4 text-muted-foreground" aria-hidden />
        <Switch
          checked={isDark}
          onCheckedChange={(checked) => setTheme(checked ? "dark" : "light")}
        />
        <Moon className="size-4 text-muted-foreground" aria-hidden />
        <span className="text-sm text-muted-foreground">
          {t(isDark ? "preferences.theme.dark" : "preferences.theme.light")}
        </span>
      </label>
    </div>
  );
}

function toFormValues(preferences: Preferences): PreferencesFormValues {
  return {
    language: preferences.language,
    stale_after_days: String(preferences.stale_after_days),
  };
}

export function PreferencesForm({ preferences }: { preferences: Preferences }) {
  const { t } = useTranslation();
  const update = useUpdatePreferences();

  const form = useForm<PreferencesFormValues>({
    resolver: zodResolver(preferencesSchema),
    defaultValues: toFormValues(preferences),
  });

  // Si otra pestaña cambia las preferencias, esta refleja el valor guardado.
  useEffect(() => {
    form.reset(toFormValues(preferences));
  }, [preferences, form]);

  const onSubmit = (values: PreferencesFormValues) => {
    update.mutate(values, {
      onSuccess: () => toast.success(t("preferences.saved")),
      onError: (error) => toast.error(t(errorMessageKey(error))),
    });
  };

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-6 max-w-md" noValidate>
      <ThemeField />
      <FormSelect
        form={form}
        name="language"
        label={t("preferences.fields.language")}
        options={LANGUAGES.map((value) => ({ value, label: t(`preferences.language.${value}`) }))}
        emptyLabel={t("preferences.language.followBrowser")}
      />
      <FormInput
        form={form}
        name="stale_after_days"
        inputMode="numeric"
        label={t("preferences.fields.staleAfterDays")}
      />
      <FormActions loading={update.isPending} submitLabel={t("common.save")} />
    </form>
  );
}
