import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { ApiError } from "@/shared/lib/apiClient";
import { errorMessageKey, errorMessageParams } from "@/shared/lib/errors";
import { FormActions, FormInput, FormTextarea } from "@/shared/components/form";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import {
  companySchema,
  emptyCompanyForm,
  type CompanyFormValues,
} from "../schemas/company.schema";
import { useCreateCompany } from "../hooks/mutations/useCreateCompany";
import { useUpdateCompany } from "../hooks/mutations/useUpdateCompany";
import type { Company } from "../types/Company";
import { LimitWarning } from "@/features/usage/components/LimitWarning";

interface CompanyFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Si se indica, el diálogo edita esta empresa; si no, crea una nueva. */
  company?: Company | null;
}

function toFormValues(company: Company | null | undefined): CompanyFormValues {
  if (!company) return emptyCompanyForm;
  return {
    name: company.name,
    website: company.website ?? "",
    location: company.location ?? "",
    notes: company.notes ?? "",
  };
}

export function CompanyFormDialog({ open, onOpenChange, company }: CompanyFormDialogProps) {
  const { t } = useTranslation();
  const create = useCreateCompany();
  const update = useUpdateCompany();
  const isEdit = !!company;

  const form = useForm<CompanyFormValues>({
    resolver: zodResolver(companySchema),
    defaultValues: toFormValues(company),
  });

  // Al abrir, el formulario refleja la empresa elegida (o queda vacío para crear).
  useEffect(() => {
    if (open) form.reset(toFormValues(company));
  }, [open, company, form]);

  const onSubmit = (values: CompanyFormValues) => {
    const options = {
      onSuccess: () => {
        toast.success(t(isEdit ? "companies.updated" : "companies.created"));
        onOpenChange(false);
      },
      onError: (error: Error) => {
        // El nombre duplicado se señala en su campo; el resto, como aviso.
        if (error instanceof ApiError && error.code === "company_name_taken") {
          form.setError("name", { message: "errors.company_name_taken" });
        } else {
          toast.error(t(errorMessageKey(error), errorMessageParams(error)));
        }
      },
    };
    if (company) update.mutate({ id: company.id, data: values }, options);
    else create.mutate(values, options);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t(isEdit ? "companies.editTitle" : "companies.newTitle")}</DialogTitle>
        </DialogHeader>
        <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-4" noValidate>
          {!isEdit && <LimitWarning limitKey="companies" />}
          <FormInput form={form} name="name" label={t("companies.fields.name")} />
          <FormInput
            form={form}
            name="website"
            type="url"
            label={t("companies.fields.website")}
            placeholder="https://"
          />
          <FormInput form={form} name="location" label={t("companies.fields.location")} />
          <FormTextarea form={form} name="notes" label={t("common.fields.notes")} rows={3} />
          <FormActions
            loading={create.isPending || update.isPending}
            submitLabel={t("common.save")}
            cancelLabel={t("common.cancel")}
            onCancel={() => onOpenChange(false)}
          />
        </form>
      </DialogContent>
    </Dialog>
  );
}
