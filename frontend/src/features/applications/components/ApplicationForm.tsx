import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { ApiError } from "@/shared/lib/apiClient";
import { errorMessageKey, errorMessageParams } from "@/shared/lib/errors";
import {
  type AsyncComboboxOption,
  FormActions,
  FormAsyncCombobox,
  FormDatePicker,
  FormInput,
  FormSelect,
  FormTextarea,
} from "@/shared/components/form";
import { companyKeys } from "@/features/companies/company.keys";
import { companyService } from "@/features/companies/services/company.service";
import { useCreateCompany } from "@/features/companies/hooks/mutations/useCreateCompany";
import { applicationSchema, type ApplicationFormValues } from "../schemas/application.schema";
import {
  APPLICATION_SOURCES,
  CURRENCIES,
  INITIAL_STATUSES,
  WORK_MODES,
  type CompanySummary,
} from "../types/Application";
import { LimitWarning } from "@/features/usage/components/LimitWarning";

// Cuelga de companyKeys.all: al crear o editar una empresa, las opciones se refrescan.
const COMPANY_OPTIONS_KEY = [...companyKeys.all, "options"] as const;

async function searchCompanies(q: string): Promise<AsyncComboboxOption[]> {
  const page = await companyService.list({ page: 1, limit: 20, q: q || undefined });
  return page.items.map((company) => ({ value: company.id, label: company.name }));
}

// Errores de la API que tienen un campo al que señalar.
const FIELD_ERRORS: Record<string, keyof ApplicationFormValues> = {
  salary_range_invalid: "salary_max",
  applied_at_required: "applied_at",
  not_found: "company_id",
};

interface ApplicationFormProps {
  mode: "create" | "edit";
  defaultValues: ApplicationFormValues;
  initialCompany?: CompanySummary | null;
  submitting: boolean;
  onSubmit: (values: ApplicationFormValues) => Promise<unknown>;
  onCancel: () => void;
}

export function ApplicationForm({
  mode,
  defaultValues,
  initialCompany,
  submitting,
  onSubmit,
  onCancel,
}: ApplicationFormProps) {
  const { t } = useTranslation();
  const createCompany = useCreateCompany();

  const form = useForm<ApplicationFormValues>({
    resolver: zodResolver(applicationSchema),
    defaultValues,
  });

  // RF-13: crear la empresa sin salir del formulario.
  const handleCreateCompany = async (name: string): Promise<AsyncComboboxOption> => {
    const company = await createCompany.mutateAsync({ name, website: "", location: "", notes: "" });
    toast.success(t("companies.created"));
    return { value: company.id, label: company.name };
  };

  const submit = async (values: ApplicationFormValues) => {
    try {
      await onSubmit(values);
    } catch (error) {
      const field = error instanceof ApiError && error.code ? FIELD_ERRORS[error.code] : undefined;
      if (field) form.setError(field, { message: errorMessageKey(error) });
      else toast.error(t(errorMessageKey(error), errorMessageParams(error)));
    }
  };

  const options = <T extends string>(values: readonly T[], prefix: string) =>
    values.map((value) => ({ value, label: t(`${prefix}.${value}`) }));

  // useWatch y no form.watch(): compatible con la memorización de React.
  const status = useWatch({ control: form.control, name: "status" });

  return (
    <form
      onSubmit={form.handleSubmit(submit)}
      className="grid gap-6 lg:grid-cols-[3fr_2fr] lg:gap-x-10"
      noValidate
    >
      {mode === "create" && (
        <LimitWarning limitKey="applications" className="lg:col-span-2" />
      )}
      <div className="grid gap-4 sm:grid-cols-2">
        <FormAsyncCombobox
          form={form}
          name="company_id"
          label={t("applications.fields.company")}
          queryKey={COMPANY_OPTIONS_KEY}
          query={searchCompanies}
          initialOption={initialCompany ? { value: initialCompany.id, label: initialCompany.name } : null}
          onCreate={handleCreateCompany}
          placeholder={t("applications.companyPlaceholder")}
        />
        <FormInput form={form} name="position_title" label={t("applications.fields.position")} />

        {mode === "create" && (
          <FormSelect
            form={form}
            name="status"
            label={t("applications.fields.initialStatus")}
            options={options(INITIAL_STATUSES, "applications.status")}
          />
        )}
        <FormDatePicker
          form={form}
          name="applied_at"
          label={t("applications.fields.appliedAt")}
          placeholder={
            status === "applied" && mode === "create" ? t("applications.appliedAtToday") : undefined
          }
        />

        <FormInput form={form} name="location" label={t("applications.fields.location")} />
        <FormSelect
          form={form}
          name="work_mode"
          label={t("applications.fields.workMode")}
          options={options(WORK_MODES, "applications.workMode")}
          emptyLabel={t("common.unspecified")}
        />
        <FormSelect
          form={form}
          name="source"
          label={t("applications.fields.source")}
          options={options(APPLICATION_SOURCES, "applications.source")}
          emptyLabel={t("common.unspecified")}
        />
        <FormInput
          form={form}
          name="job_url"
          type="url"
          label={t("applications.fields.jobUrl")}
          placeholder="https://"
        />
      </div>

      <div className="grid content-start gap-6">
        <fieldset className="grid gap-4 sm:grid-cols-3">
          <legend className="mb-2 text-sm font-medium">{t("applications.fields.salary")}</legend>
          <FormInput form={form} name="salary_min" inputMode="numeric" label={t("applications.fields.salaryMin")} />
          <FormInput form={form} name="salary_max" inputMode="numeric" label={t("applications.fields.salaryMax")} />
          <FormSelect
            form={form}
            name="salary_currency"
            label={t("applications.fields.currency")}
            options={CURRENCIES.map((value) => ({ value, label: value }))}
          />
        </fieldset>

        <FormTextarea form={form} name="notes" label={t("common.fields.notes")} rows={5} />
      </div>

      <div className="lg:col-span-2">
        <FormActions
          loading={submitting}
          submitLabel={t(mode === "create" ? "applications.create" : "common.save")}
          cancelLabel={t("common.cancel")}
          onCancel={onCancel}
        />
      </div>
    </form>
  );
}
