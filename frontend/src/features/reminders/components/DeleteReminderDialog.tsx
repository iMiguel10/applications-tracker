import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { errorMessageKey, errorMessageParams } from "@/shared/lib/errors";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/shared/components/ui/alert-dialog";
import { useDeleteReminder } from "../hooks/mutations/useDeleteReminder";

interface DeleteReminderDialogProps {
  reminderId: string | null;
  onOpenChange: (open: boolean) => void;
}

/** Borrado definitivo de un recordatorio en cualquier estado (decisión 0011): es
 * lo que libera espacio del límite, que cuenta también los hechos y descartados. */
export function DeleteReminderDialog({ reminderId, onOpenChange }: DeleteReminderDialogProps) {
  const { t } = useTranslation();
  const remove = useDeleteReminder();

  const confirm = () => {
    if (!reminderId) return;
    remove.mutate(reminderId, {
      onSuccess: () => {
        toast.success(t("reminders.deleted"));
        onOpenChange(false);
      },
      onError: (error) => toast.error(t(errorMessageKey(error), errorMessageParams(error))),
    });
  };

  return (
    <AlertDialog open={reminderId !== null} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{t("reminders.deleteTitle")}</AlertDialogTitle>
          <AlertDialogDescription>{t("reminders.deleteConfirm")}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>{t("common.cancel")}</AlertDialogCancel>
          <AlertDialogAction variant="destructive" onClick={confirm} disabled={remove.isPending}>
            {t("common.delete")}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
