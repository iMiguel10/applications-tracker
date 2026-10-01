import { useState } from "react";
import { useForm, useController, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { AlertTriangle } from "lucide-react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { errorMessageKey, errorMessageParams } from "@/shared/lib/errors";
import { cn } from "@/shared/lib/utils";
import { FormActions, FormInput, FormSelect } from "@/shared/components/form";
import { Badge } from "@/shared/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import { ErrorState } from "@/shared/components/common/ErrorState";
import { ListSkeleton } from "@/shared/components/common/Skeletons";
import { useProfile } from "@/features/profile/hooks/queries/useProfile";
import { useProfileEntries } from "@/features/profile/hooks/queries/useProfileEntries";
import {
  useProfileLanguages,
  useProfileSkills,
} from "@/features/profile/hooks/queries/useProfileSkills";
import { LimitWarning } from "@/features/usage/components/LimitWarning";
import { useGenerateCv } from "../hooks/mutations/useGenerateCv";
import { useCvDesigns } from "../hooks/queries/useCvDesigns";
import { defaultCvName, fullSelection, toRequest } from "../lib/cvSelection";
import { designName, uiCvLanguage } from "../lib/designName";
import { generateCvSchema, type GenerateCvFormValues } from "../schemas/generateCv.schema";
import type { CvDesign, LibraryDocument } from "../types/Document";
import type { Profile } from "@/features/profile/types/Profile";
import type { ProfileEntry } from "@/features/profile/types/ProfileEntry";
import type { ProfileLanguage, ProfileSkill } from "@/features/profile/types/ProfileSkill";
import { CvContentPicker } from "./CvContentPicker";

interface GenerateCvDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Tras pedirlo: p. ej. ir a la biblioteca desde el perfil. */
  onGenerated?: (document: LibraryDocument) => void;
}

/**
 * Generar un CV desde el perfil (RF-103): diseño, idioma de las etiquetas, nombre
 * y qué secciones y elementos incluir. El CV llega a la biblioteca como
 * "Generando…" y el worker lo maqueta (A35).
 */
export function GenerateCvDialog({ open, onOpenChange, onGenerated }: GenerateCvDialogProps) {
  const { t } = useTranslation();
  const designs = useCvDesigns();
  const profile = useProfile();
  const entries = useProfileEntries();
  const skills = useProfileSkills();
  const languages = useProfileLanguages();

  const queries = [designs, profile, entries, skills, languages];
  const loading = queries.some((query) => query.isLoading);
  const failed = queries.some((query) => query.isError);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{t("documents.generate.title")}</DialogTitle>
          <DialogDescription>{t("documents.generate.description")}</DialogDescription>
        </DialogHeader>

        {loading && <ListSkeleton rows={4} />}
        {failed && (
          <ErrorState
            onRetry={() => queries.forEach((query) => void query.refetch())}
            retrying={queries.some((query) => query.isFetching)}
          />
        )}
        {/* Se monta al abrir: cada vez empieza con el primer diseño apto para ATS,
            todo marcado y el nombre por defecto, sin un efecto que lo reinicie. */}
        {open &&
          designs.data &&
          profile.data &&
          entries.data &&
          skills.data &&
          languages.data && (
            <GenerateCvForm
              designs={designs.data}
              profile={profile.data}
              entries={entries.data}
              skills={skills.data}
              languages={languages.data}
              onCancel={() => onOpenChange(false)}
              onGenerated={(document) => {
                onGenerated?.(document);
                onOpenChange(false);
              }}
            />
          )}
      </DialogContent>
    </Dialog>
  );
}

interface GenerateCvFormProps {
  designs: CvDesign[];
  profile: Profile;
  entries: ProfileEntry[];
  skills: ProfileSkill[];
  languages: ProfileLanguage[];
  onCancel: () => void;
  onGenerated: (document: LibraryDocument) => void;
}

function GenerateCvForm({
  designs,
  profile,
  entries,
  skills,
  languages,
  onCancel,
  onGenerated,
}: GenerateCvFormProps) {
  const { t, i18n } = useTranslation();
  const uiLanguage = uiCvLanguage(i18n.language);
  const generate = useGenerateCv();
  const [selection, setSelection] = useState(fullSelection);
  // El nombre se rellena con el diseño elegido hasta que el usuario lo toca.
  const [nameTouched, setNameTouched] = useState(false);
  const first = designs.find((item) => item.ats_friendly) ?? designs[0];

  const form = useForm<GenerateCvFormValues>({
    resolver: zodResolver(generateCvSchema),
    defaultValues: {
      name: first ? defaultCvName(designName(first, first.key, uiLanguage)) : "",
      design: first?.key ?? "",
      language: first?.languages.includes(uiLanguage)
        ? uiLanguage
        : (first?.languages[0] ?? uiLanguage),
    },
  });
  const designKey = useWatch({ control: form.control, name: "design" });
  const design = designs.find((item) => item.key === designKey);

  const chooseDesign = (next: CvDesign) => {
    form.setValue("design", next.key, { shouldValidate: true });
    if (!next.languages.includes(form.getValues("language"))) {
      form.setValue("language", next.languages[0] ?? uiLanguage);
    }
    if (!nameTouched) {
      form.setValue("name", defaultCvName(designName(next, next.key, uiLanguage)));
    }
  };

  const onSubmit = (values: GenerateCvFormValues) => {
    generate.mutate(
      { ...values, ...toRequest(selection) },
      {
        onSuccess: (document) => {
          toast.success(t("documents.generate.started"));
          onGenerated(document);
        },
        onError: (error) => toast.error(t(errorMessageKey(error), errorMessageParams(error))),
      },
    );
  };

  return (
    <form
      onSubmit={(event) => {
        // Puede abrirse dentro de otro formulario (como la subida): en React el
        // submit sube por el árbol de componentes aunque esto sea un portal.
        event.stopPropagation();
        void form.handleSubmit(onSubmit)(event);
      }}
      className="grid gap-5"
      noValidate
    >
      <LimitWarning limitKey="documents" />
      <LimitWarning limitKey="storage_bytes" />

      <DesignPicker form={form} designs={designs} language={uiLanguage} onChoose={chooseDesign} />
      {design && !design.ats_friendly && (
        <p
          role="status"
          className="flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-800 dark:text-amber-300"
        >
          <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden />
          <span>{t("documents.generate.notAtsWarning")}</span>
        </p>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <div onChangeCapture={() => setNameTouched(true)}>
          <FormInput form={form} name="name" label={t("documents.fields.name")} />
        </div>
        <FormSelect
          form={form}
          name="language"
          label={t("documents.generate.language")}
          options={(design?.languages ?? [uiLanguage]).map((language) => ({
            value: language,
            label: t(`documents.generate.languages.${language}`, { defaultValue: language }),
          }))}
        />
      </div>
      <p className="-mt-3 text-sm text-muted-foreground">{t("documents.generate.languageHint")}</p>

      <fieldset className="grid gap-2">
        <legend className="mb-2 text-sm font-medium">{t("documents.generate.content")}</legend>
        <CvContentPicker
          profile={profile}
          entries={entries}
          skills={skills}
          languages={languages}
          value={selection}
          onChange={setSelection}
        />
      </fieldset>

      <FormActions
        loading={generate.isPending}
        submitLabel={t("documents.generate.submit")}
        cancelLabel={t("common.cancel")}
        onCancel={onCancel}
      />
    </form>
  );
}

function DesignPicker({
  form,
  designs,
  language,
  onChoose,
}: {
  form: ReturnType<typeof useForm<GenerateCvFormValues>>;
  designs: CvDesign[];
  language: string;
  onChoose: (design: CvDesign) => void;
}) {
  const { t } = useTranslation();
  const {
    field,
    fieldState: { error },
  } = useController({ control: form.control, name: "design" });

  return (
    <fieldset className="grid gap-2" aria-describedby={error ? "design-error" : undefined}>
      <legend className="mb-2 text-sm font-medium">{t("documents.generate.design")}</legend>
      <div className="grid gap-2 sm:grid-cols-2">
        {designs.map((design) => {
          const selected = field.value === design.key;
          return (
            <label
              key={design.key}
              className={cn(
                "grid cursor-pointer gap-1 rounded-lg border p-3 text-sm transition-colors has-[:focus-visible]:ring-3 has-[:focus-visible]:ring-ring/50",
                selected ? "border-primary bg-primary/5" : "hover:bg-muted/50",
              )}
            >
              <span className="flex items-center justify-between gap-2">
                <span className="flex items-center gap-2 font-medium">
                  <input
                    type="radio"
                    name={field.name}
                    value={design.key}
                    checked={selected}
                    onChange={() => onChoose(design)}
                    onBlur={field.onBlur}
                    className="accent-primary"
                  />
                  {designName(design, design.key, language)}
                </span>
                <Badge variant={design.ats_friendly ? "secondary" : "outline"}>
                  {t(design.ats_friendly ? "documents.generate.ats" : "documents.generate.notAts")}
                </Badge>
              </span>
              <span className="text-muted-foreground">
                {design.descriptions[language] ?? design.descriptions.en}
              </span>
            </label>
          );
        })}
      </div>
      {error && (
        <p id="design-error" className="text-sm text-destructive">
          {t(error.message ?? "")}
        </p>
      )}
    </fieldset>
  );
}
