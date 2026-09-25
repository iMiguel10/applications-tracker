import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { errorMessageKey, errorMessageParams } from "@/shared/lib/errors";
import {
  type AsyncComboboxOption,
  FormActions,
  FormAsyncCombobox,
  FormDateTimePicker,
  FormInput,
} from "@/shared/components/form";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import { applicationKeys } from "@/features/applications/application.keys";
import { DEFAULT_LIST_PARAMS } from "@/features/applications/lib/listParams";
import { applicationService } from "@/features/applications/services/application.service";
import {
  emptyReminderForm,
  reminderSchema,
  type ReminderFormValues,
} from "../schemas/reminder.schema";
import { useCreateReminder } from "../hooks/mutations/useCreateReminder";
import { LimitWarning } from "@/features/usage/components/LimitWarning";

const APPLICATION_OPTIONS_KEY = [...applicationKeys.all, "options"] as const;

async function searchApplications(q: string): Promise<AsyncComboboxOption[]> {
  const page = await applicationService.list({ ...DEFAULT_LIST_PARAMS, limit: 20, q });
  return page.items.map((application) => ({
    value: application.id,
    label: `${application.position_title} · ${application.company.name}`,
  }));
}

interface ReminderFormDialogProps {
  /**
   * Solicitud a la que queda ligado el recordatorio (RF-50). Fija (el detalle de
   * la solicitud, F4) si se indica; si se omite, el formulario deja elegir una o
   * dejarlo sin ligar (el listado global, F5).
   */
  applicationId?: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ReminderFormDialog({
  applicationId,
  open,
  onOpenChange,
}: ReminderFormDialogProps) {
  const { t } = useTranslation();
  const create = useCreateReminder();

  const form = useForm<ReminderFormValues>({
    resolver: zodResolver(reminderSchema),
    defaultValues: emptyReminderForm,
  });

  useEffect(() => {
    if (open) {
      form.reset({ ...emptyReminderForm, application_id: applicationId ?? "" });
    }
  }, [open, applicationId, form]);

  const onSubmit = (values: ReminderFormValues) =>
    create.mutate(values, {
      onSuccess: () => {
        toast.success(t("reminders.created"));
        onOpenChange(false);
      },
      onError: (error) => toast.error(t(errorMessageKey(error), errorMessageParams(error))),
    });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("reminders.newTitle")}</DialogTitle>
        </DialogHeader>
        <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-4" noValidate>
          <LimitWarning limitKey="reminders" />
          <FormInput form={form} name="title" label={t("reminders.fields.title")} />
          <FormDateTimePicker
            form={form}
            name="due_at"
            label={t("reminders.fields.dueAt")}
          />
          {applicationId === undefined && (
            <FormAsyncCombobox
              form={form}
              name="application_id"
              label={t("reminders.fields.application")}
              queryKey={APPLICATION_OPTIONS_KEY}
              query={searchApplications}
              placeholder={t("reminders.applicationPlaceholder")}
            />
          )}
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
