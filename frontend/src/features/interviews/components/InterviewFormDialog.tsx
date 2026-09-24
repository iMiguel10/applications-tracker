import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { errorMessageKey } from "@/shared/lib/errors";
import { toDateTimeLocal } from "@/shared/lib/dates";
import {
  FormActions,
  FormDateTimePicker,
  FormInput,
  FormSelect,
  FormTextarea,
} from "@/shared/components/form";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import {
  emptyInterviewForm,
  interviewSchema,
  type InterviewFormValues,
} from "../schemas/interview.schema";
import { useCreateInterview } from "../hooks/mutations/useCreateInterview";
import { useUpdateInterview } from "../hooks/mutations/useUpdateInterview";
import {
  INTERVIEW_FORMATS,
  INTERVIEW_OUTCOMES,
  INTERVIEW_TYPES,
  type Interview,
} from "../types/Interview";

interface InterviewFormDialogProps {
  applicationId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Si se indica, el diálogo edita esta entrevista; si no, crea una nueva. */
  interview?: Interview | null;
  /** Solo se llama tras CREAR con éxito (RF-42), nunca al editar ni al cancelar. */
  onCreated?: () => void;
}

function toFormValues(interview: Interview | null | undefined): InterviewFormValues {
  if (!interview) return emptyInterviewForm;
  return {
    scheduled_at: toDateTimeLocal(interview.scheduled_at),
    duration_minutes: interview.duration_minutes?.toString() ?? "",
    interviewers: interview.interviewers ?? "",
    interview_type: interview.interview_type,
    format: interview.format,
    outcome: interview.outcome,
    notes: interview.notes ?? "",
  };
}

export function InterviewFormDialog({
  applicationId,
  open,
  onOpenChange,
  interview,
  onCreated,
}: InterviewFormDialogProps) {
  const { t } = useTranslation();
  const create = useCreateInterview(applicationId);
  const update = useUpdateInterview(applicationId);
  const isEdit = !!interview;

  const form = useForm<InterviewFormValues>({
    resolver: zodResolver(interviewSchema),
    defaultValues: toFormValues(interview),
  });

  useEffect(() => {
    if (open) form.reset(toFormValues(interview));
  }, [open, interview, form]);

  const options = <T extends string>(values: readonly T[], prefix: string) =>
    values.map((value) => ({ value, label: t(`${prefix}.${value}`) }));

  const onSubmit = (values: InterviewFormValues) => {
    const onError = (error: Error) => toast.error(t(errorMessageKey(error)));
    if (interview) {
      update.mutate(
        { interviewId: interview.id, values },
        {
          onSuccess: () => {
            toast.success(t("interviews.updated"));
            onOpenChange(false);
          },
          onError,
        },
      );
    } else {
      create.mutate(values, {
        onSuccess: () => {
          toast.success(t("interviews.created"));
          onOpenChange(false);
          onCreated?.();
        },
        onError,
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t(isEdit ? "interviews.editTitle" : "interviews.newTitle")}</DialogTitle>
        </DialogHeader>
        <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-4" noValidate>
          <FormDateTimePicker
            form={form}
            name="scheduled_at"
            label={t("interviews.fields.scheduledAt")}
          />
          <FormInput
            form={form}
            name="duration_minutes"
            inputMode="numeric"
            label={t("interviews.fields.duration")}
          />
          <FormInput
            form={form}
            name="interviewers"
            label={t("interviews.fields.interviewers")}
            placeholder={t("interviews.interviewersPlaceholder")}
          />
          <FormSelect
            form={form}
            name="interview_type"
            label={t("interviews.fields.type")}
            options={options(INTERVIEW_TYPES, "interviews.type")}
            emptyLabel={t("common.unspecified")}
          />
          <FormSelect
            form={form}
            name="format"
            label={t("interviews.fields.format")}
            options={options(INTERVIEW_FORMATS, "interviews.format")}
            emptyLabel={t("common.unspecified")}
          />
          {isEdit && (
            <FormSelect
              form={form}
              name="outcome"
              label={t("interviews.fields.outcome")}
              options={options(INTERVIEW_OUTCOMES, "interviews.outcome")}
            />
          )}
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
