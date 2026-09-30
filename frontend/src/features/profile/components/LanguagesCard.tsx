import { useEffect, useMemo } from "react";
import { useFieldArray, useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { FormActions, FormSelect } from "@/shared/components/form";
import { SortableList } from "@/shared/components/common/SortableList";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Input } from "@/shared/components/ui/input";
import { errorMessageKey, errorMessageParams } from "@/shared/lib/errors";
import { useSaveLanguages } from "../hooks/mutations/useSaveSkills";
import {
  languagesSchema,
  toLanguagesForm,
  type LanguagesFormValues,
} from "../schemas/skills.schema";
import { LANGUAGE_LEVELS, MAX_LANGUAGES, type ProfileLanguage } from "../types/ProfileSkill";

/** Idiomas con su nivel (RF-102): la lista se edita entera y se guarda con un botón. */
export function LanguagesCard({ languages }: { languages: ProfileLanguage[] }) {
  const { t } = useTranslation();
  const save = useSaveLanguages();
  const form = useForm<LanguagesFormValues>({
    resolver: zodResolver(languagesSchema),
    defaultValues: toLanguagesForm(languages),
  });
  const rows = useFieldArray({ control: form.control, name: "languages", keyName: "key" });
  const values = useWatch({ control: form.control, name: "languages" });

  useEffect(() => {
    if (!form.formState.isDirty) form.reset(toLanguagesForm(languages));
  }, [languages, form]);

  const levels = useMemo(
    () => LANGUAGE_LEVELS.map((value) => ({ value, label: t(`profile.languages.levels.${value}`) })),
    [t],
  );

  const onSubmit = (data: LanguagesFormValues) => {
    save.mutate(data, {
      onSuccess: (saved) => {
        form.reset(toLanguagesForm(saved));
        toast.success(t("profile.languages.saved"));
      },
      onError: (error) => toast.error(t(errorMessageKey(error), errorMessageParams(error))),
    });
  };

  const labelOf = (index: number) =>
    values?.[index]?.language || t("profile.languages.languageN", { n: index + 1 });

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h2>{t("profile.languages.section")}</h2>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-3" noValidate>
          <SortableList
            items={rows.fields.map((field, index) => ({ id: field.key, label: labelOf(index) }))}
            onMove={(from, to) => rows.move(from, to)}
            className="grid gap-2"
            renderItem={(item, handle) => {
              const index = rows.fields.findIndex((field) => field.key === item.id);
              const error = form.formState.errors.languages?.[index]?.language;
              const id = `languages.${index}.language`;
              return (
                <div className="flex items-start gap-2">
                  <div className="pt-0.5">{handle}</div>
                  <div className="grid flex-1 gap-2 sm:grid-cols-[1fr_14rem]">
                    <div className="grid gap-1">
                      <Input
                        id={id}
                        aria-label={t("profile.languages.languageN", { n: index + 1 })}
                        placeholder={t("profile.languages.language")}
                        aria-invalid={!!error}
                        aria-describedby={error ? `${id}-error` : undefined}
                        {...form.register(`languages.${index}.language`)}
                      />
                      {error && (
                        <p id={`${id}-error`} className="text-sm text-destructive">
                          {t(error.message ?? "")}
                        </p>
                      )}
                    </div>
                    <FormSelect
                      form={form}
                      name={`languages.${index}.level`}
                      label={t("profile.languages.levelOf", { n: index + 1 })}
                      hideLabel
                      options={levels}
                      placeholder={t("profile.languages.level")}
                    />
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    aria-label={t("profile.languages.remove", { label: item.label })}
                    onClick={() => rows.remove(index)}
                  >
                    <Trash2 aria-hidden />
                  </Button>
                </div>
              );
            }}
          />
          <Button
            type="button"
            variant="outline"
            className="w-fit"
            disabled={rows.fields.length >= MAX_LANGUAGES}
            onClick={() => rows.append({ language: "", level: null })}
          >
            <Plus aria-hidden />
            {t("profile.languages.add")}
          </Button>
          <FormActions loading={save.isPending} submitLabel={t("common.save")} />
        </form>
      </CardContent>
    </Card>
  );
}
