import { useEffect, useMemo } from "react";
import { useController, useFieldArray, useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { FormActions, FormInput, FormSelect, FormTextarea } from "@/shared/components/form";
import { SortableList } from "@/shared/components/common/SortableList";
import { Button } from "@/shared/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/shared/components/ui/dialog";
import { Label } from "@/shared/components/ui/label";
import { Switch } from "@/shared/components/ui/switch";
import { Textarea } from "@/shared/components/ui/textarea";
import { errorMessageKey, errorMessageParams } from "@/shared/lib/errors";
import { useSaveEntry } from "../hooks/mutations/useSaveEntry";
import { monthOptions, yearOptions } from "../lib/months";
import {
  entrySchema,
  toEntryForm,
  toEntryInput,
  type EntryFormValues,
} from "../schemas/entry.schema";
import {
  MAX_BULLETS_PER_ENTRY,
  type EntryKind,
  type ProfileEntry,
} from "../types/ProfileEntry";

type Props = {
  kind: EntryKind;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Si se indica, edita esta entrada; si no, crea una nueva en la sección. */
  entry?: ProfileEntry | null;
};

export function EntryFormDialog({ kind, open, onOpenChange, entry }: Props) {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "es";
  const months = useMemo(() => monthOptions(locale), [locale]);
  const years = useMemo(() => yearOptions(), []);
  const save = useSaveEntry();

  const form = useForm<EntryFormValues>({
    resolver: zodResolver(entrySchema),
    defaultValues: toEntryForm(entry ?? null),
  });
  const bullets = useFieldArray({ control: form.control, name: "bullets", keyName: "key" });
  const bulletValues = useWatch({ control: form.control, name: "bullets" });
  const isCurrent = useWatch({ control: form.control, name: "is_current" });
  const current = useController({ control: form.control, name: "is_current" });

  // Al abrir, el formulario refleja la entrada elegida (o queda vacío para crear).
  useEffect(() => {
    if (open) form.reset(toEntryForm(entry ?? null));
  }, [open, entry, form]);

  const onSubmit = (values: EntryFormValues) => {
    save.mutate(
      { kind, id: entry?.id, input: toEntryInput(values) },
      {
        onSuccess: () => {
          toast.success(t("profile.entries.saved"));
          onOpenChange(false);
        },
        onError: (error) => toast.error(t(errorMessageKey(error), errorMessageParams(error))),
      },
    );
  };

  const section = `profile.entries.${kind}`;
  const bulletLabel = (index: number) =>
    bulletValues?.[index]?.text || t("profile.entries.bulletN", { n: index + 1 });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{t(entry ? `${section}.editTitle` : `${section}.newTitle`)}</DialogTitle>
        </DialogHeader>
        <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-4" noValidate>
          <FormInput form={form} name="title" label={t(`${section}.titleField`)} />
          <div className="grid gap-4 sm:grid-cols-2">
            <FormInput
              form={form}
              name="organization"
              label={t(`${section}.organizationField`)}
            />
            <FormInput form={form} name="location" label={t("profile.entries.location")} />
          </div>

          <fieldset className="grid gap-3">
            <legend className="mb-2 text-sm font-medium">{t("profile.entries.dates")}</legend>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="grid grid-cols-2 gap-2">
                <FormSelect
                  form={form}
                  name="start_month"
                  label={t("profile.entries.startMonth")}
                  options={months}
                  emptyLabel="—"
                />
                <FormSelect
                  form={form}
                  name="start_year"
                  label={t("profile.entries.startYear")}
                  options={years}
                  emptyLabel="—"
                />
              </div>
              {!isCurrent && (
                <div className="grid grid-cols-2 gap-2">
                  <FormSelect
                    form={form}
                    name="end_month"
                    label={t("profile.entries.endMonth")}
                    options={months}
                    emptyLabel="—"
                  />
                  <FormSelect
                    form={form}
                    name="end_year"
                    label={t("profile.entries.endYear")}
                    options={years}
                    emptyLabel="—"
                  />
                </div>
              )}
            </div>
            <label className="flex w-fit cursor-pointer items-center gap-3 text-sm">
              <Switch
                checked={current.field.value}
                onCheckedChange={(checked) => current.field.onChange(checked)}
              />
              {t(`${section}.current`)}
            </label>
          </fieldset>

          <FormTextarea
            form={form}
            name="description"
            label={t("profile.entries.description")}
            rows={3}
          />

          <fieldset className="grid gap-3">
            <legend className="text-sm font-medium">{t("profile.entries.bullets")}</legend>
            <p className="text-sm text-muted-foreground">{t("profile.entries.bulletsHint")}</p>
            <SortableList
              items={bullets.fields.map((field, index) => ({
                id: field.key,
                label: bulletLabel(index),
              }))}
              onMove={(from, to) => bullets.move(from, to)}
              className="grid gap-2"
              renderItem={(item, handle) => {
                const index = bullets.fields.findIndex((field) => field.key === item.id);
                const error = form.formState.errors.bullets?.[index]?.text;
                const id = `bullets.${index}.text`;
                return (
                  <div className="flex items-start gap-2">
                    <div className="pt-1">{handle}</div>
                    <div className="grid flex-1 gap-1">
                      <Label htmlFor={id} className="sr-only">
                        {t("profile.entries.bulletN", { n: index + 1 })}
                      </Label>
                      <Textarea
                        id={id}
                        rows={2}
                        aria-invalid={!!error}
                        aria-describedby={error ? `${id}-error` : undefined}
                        {...form.register(`bullets.${index}.text`)}
                      />
                      {error && (
                        <p id={`${id}-error`} className="text-sm text-destructive">
                          {t(error.message ?? "")}
                        </p>
                      )}
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      aria-label={t("profile.entries.removeBullet", { n: index + 1 })}
                      onClick={() => bullets.remove(index)}
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
              disabled={bullets.fields.length >= MAX_BULLETS_PER_ENTRY}
              onClick={() => bullets.append({ text: "" })}
            >
              <Plus aria-hidden />
              {t("profile.entries.addBullet")}
            </Button>
          </fieldset>

          <FormActions
            loading={save.isPending}
            submitLabel={t("common.save")}
            cancelLabel={t("common.cancel")}
            onCancel={() => onOpenChange(false)}
          />
        </form>
      </DialogContent>
    </Dialog>
  );
}
