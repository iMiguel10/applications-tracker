import { useEffect, useMemo } from "react";
import { useFieldArray, useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { FormActions, FormSelect } from "@/shared/components/form";
import { SortableList } from "@/shared/components/common/SortableList";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Input } from "@/shared/components/ui/input";
import { errorMessageKey, errorMessageParams } from "@/shared/lib/errors";
import { useSaveSkills } from "../hooks/mutations/useSaveSkills";
import { skillsSchema, toSkillsForm, type SkillsFormValues } from "../schemas/skills.schema";
import { MAX_SKILLS, SKILL_LEVELS, type ProfileSkill } from "../types/ProfileSkill";

const CATEGORY_SUGGESTIONS_ID = "profile-skill-categories";

/** Habilidades (RF-102): una lista que se edita entera y se guarda con un botón. */
export function SkillsCard({ skills }: { skills: ProfileSkill[] }) {
  const { t } = useTranslation();
  const save = useSaveSkills();
  const form = useForm<SkillsFormValues>({
    resolver: zodResolver(skillsSchema),
    defaultValues: toSkillsForm(skills),
  });
  const rows = useFieldArray({ control: form.control, name: "skills", keyName: "key" });
  const values = useWatch({ control: form.control, name: "skills" });

  // Lo guardado (con los ids de las nuevas) sustituye al formulario, salvo que se
  // esté editando.
  useEffect(() => {
    if (!form.formState.isDirty) form.reset(toSkillsForm(skills));
  }, [skills, form]);

  const levels = useMemo(
    () => SKILL_LEVELS.map((value) => ({ value, label: t(`profile.skills.levels.${value}`) })),
    [t],
  );
  // Las categorías ya escritas se sugieren al escribir otra: así se repiten igual
  // y el CV las agrupa bien.
  const categories = useMemo(
    () => [...new Set((values ?? []).map((skill) => skill.category.trim()).filter(Boolean))],
    [values],
  );

  const onSubmit = (data: SkillsFormValues) => {
    save.mutate(data, {
      onSuccess: (saved) => {
        form.reset(toSkillsForm(saved));
        toast.success(t("profile.skills.saved"));
      },
      onError: (error) => toast.error(t(errorMessageKey(error), errorMessageParams(error))),
    });
  };

  const labelOf = (index: number) =>
    values?.[index]?.name || t("profile.skills.skillN", { n: index + 1 });

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h2>{t("profile.skills.section")}</h2>
        </CardTitle>
        <CardDescription>{t("profile.skills.hint")}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-3" noValidate>
          <datalist id={CATEGORY_SUGGESTIONS_ID}>
            {categories.map((category) => (
              <option key={category} value={category} />
            ))}
          </datalist>
          {rows.fields.length > 0 && (
            <div
              aria-hidden
              className="hidden gap-2 pl-10 pr-10 text-xs font-medium text-muted-foreground sm:grid sm:grid-cols-[1fr_1fr_10rem]"
            >
              <span>{t("profile.skills.name")}</span>
              <span>{t("profile.skills.category")}</span>
              <span>{t("profile.skills.level")}</span>
            </div>
          )}
          <SortableList
            items={rows.fields.map((field, index) => ({ id: field.key, label: labelOf(index) }))}
            onMove={(from, to) => rows.move(from, to)}
            className="grid gap-2"
            renderItem={(item, handle) => {
              const index = rows.fields.findIndex((field) => field.key === item.id);
              const errors = form.formState.errors.skills?.[index];
              const nameError = errors?.name;
              const nameId = `skills.${index}.name`;
              return (
                <div className="flex items-start gap-2">
                  <div className="pt-0.5">{handle}</div>
                  <div className="grid flex-1 gap-2 sm:grid-cols-[1fr_1fr_10rem]">
                    <div className="grid gap-1">
                      <Input
                        id={nameId}
                        aria-label={t("profile.skills.nameOf", { n: index + 1 })}
                        placeholder={t("profile.skills.name")}
                        aria-invalid={!!nameError}
                        aria-describedby={nameError ? `${nameId}-error` : undefined}
                        {...form.register(`skills.${index}.name`)}
                      />
                      {nameError && (
                        <p id={`${nameId}-error`} className="text-sm text-destructive">
                          {t(nameError.message ?? "")}
                        </p>
                      )}
                    </div>
                    <Input
                      aria-label={t("profile.skills.categoryOf", { n: index + 1 })}
                      placeholder={t("profile.skills.category")}
                      list={CATEGORY_SUGGESTIONS_ID}
                      {...form.register(`skills.${index}.category`)}
                    />
                    <FormSelect
                      form={form}
                      name={`skills.${index}.level`}
                      label={t("profile.skills.levelOf", { n: index + 1 })}
                      hideLabel
                      options={levels}
                      emptyLabel={t("profile.skills.noLevel")}
                    />
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    aria-label={t("profile.skills.remove", { label: item.label })}
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
            disabled={rows.fields.length >= MAX_SKILLS}
            onClick={() => rows.append({ name: "", category: "", level: null })}
          >
            <Plus aria-hidden />
            {t("profile.skills.add")}
          </Button>
          <FormActions loading={save.isPending} submitLabel={t("common.save")} />
        </form>
      </CardContent>
    </Card>
  );
}
