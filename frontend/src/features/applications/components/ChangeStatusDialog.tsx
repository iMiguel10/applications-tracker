import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { errorMessageKey } from "@/shared/lib/errors";
import { FormActions, FormDatePicker, FormSelect, FormTextarea } from "@/shared/components/form";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import {
  emptyStatusChangeForm,
  statusChangeSchema,
  type StatusChangeFormValues,
} from "../schemas/statusChange.schema";
import { useChangeStatus } from "../hooks/mutations/useChangeStatus";
import type { Application } from "../types/Application";

interface ChangeStatusDialogProps {
  application: Application;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ChangeStatusDialog({ application, open, onOpenChange }: ChangeStatusDialogProps) {
  const { t } = useTranslation();
  const changeStatus = useChangeStatus();

  const form = useForm<StatusChangeFormValues>({
    resolver: zodResolver(statusChangeSchema),
    defaultValues: emptyStatusChangeForm,
  });

  // Cada apertura empieza en blanco: no arrastra el estado elegido la vez anterior.
  useEffect(() => {
    if (open) form.reset(emptyStatusChangeForm);
  }, [open, form]);

  const options = application.allowed_transitions.map((status) => ({
    value: status,
    label: t(`applications.status.${status}`),
  }));

  const onSubmit = (values: StatusChangeFormValues) =>
    changeStatus.mutate(
      { applicationId: application.id, values },
      {
        onSuccess: () => {
          toast.success(t("applications.statusChanged"));
          onOpenChange(false);
        },
        onError: (error) => toast.error(t(errorMessageKey(error))),
      },
    );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("applications.changeStatusTitle")}</DialogTitle>
        </DialogHeader>
        <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-4" noValidate>
          <FormSelect
            form={form}
            name="to_status"
            label={t("applications.fields.newStatus")}
            options={options}
          />
          <FormDatePicker
            form={form}
            name="changed_at"
            label={t("applications.fields.changedAt")}
            placeholder={t("applications.changedAtNow")}
          />
          <FormTextarea form={form} name="note" label={t("common.fields.notes")} rows={3} />
          <FormActions
            loading={changeStatus.isPending}
            submitLabel={t("applications.changeStatus")}
            cancelLabel={t("common.cancel")}
            onCancel={() => onOpenChange(false)}
          />
        </form>
      </DialogContent>
    </Dialog>
  );
}
