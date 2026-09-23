import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { errorMessageKey } from "@/shared/lib/errors";
import { FormActions, FormInput } from "@/shared/components/form";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import {
  emptyReminderForm,
  reminderSchema,
  type ReminderFormValues,
} from "../schemas/reminder.schema";
import { useCreateReminder } from "../hooks/mutations/useCreateReminder";

interface ReminderFormDialogProps {
  /** Solicitud a la que queda ligado el recordatorio (RF-50). `null`: sin ligar. */
  applicationId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ReminderFormDialog({
  applicationId,
  open,
  onOpenChange,
}: ReminderFormDialogProps) {
  const { t } = useTranslation();
  const create = useCreateReminder(applicationId);

  const form = useForm<ReminderFormValues>({
    resolver: zodResolver(reminderSchema),
    defaultValues: emptyReminderForm,
  });

  useEffect(() => {
    if (open) form.reset(emptyReminderForm);
  }, [open, form]);

  const onSubmit = (values: ReminderFormValues) =>
    create.mutate(values, {
      onSuccess: () => {
        toast.success(t("reminders.created"));
        onOpenChange(false);
      },
      onError: (error) => toast.error(t(errorMessageKey(error))),
    });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("reminders.newTitle")}</DialogTitle>
        </DialogHeader>
        <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-4" noValidate>
          <FormInput form={form} name="title" label={t("reminders.fields.title")} />
          <FormInput
            form={form}
            name="due_at"
            type="datetime-local"
            label={t("reminders.fields.dueAt")}
          />
          <FormActions
            loading={create.isPending}
            submitLabel={t("common.save")}
            cancelLabel={t("common.cancel")}
            onCancel={() => onOpenChange(false)}
          />
        </form>
      </DialogContent>
    </Dialog>
  );
}
