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
import { useUndoLastStatusChange } from "../hooks/mutations/useUndoLastStatusChange";

interface UndoStatusChangeDialogProps {
  applicationId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function UndoStatusChangeDialog({
  applicationId,
  open,
  onOpenChange,
}: UndoStatusChangeDialogProps) {
  const { t } = useTranslation();
  const undo = useUndoLastStatusChange();

  const confirm = () =>
    undo.mutate(applicationId, {
      onSuccess: () => {
        toast.success(t("applications.statusChangeUndone"));
        onOpenChange(false);
      },
      onError: (error) => {
        toast.error(t(errorMessageKey(error), errorMessageParams(error)));
        onOpenChange(false);
      },
    });

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{t("applications.undoLastTitle")}</AlertDialogTitle>
          <AlertDialogDescription>{t("applications.undoLastConfirm")}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>{t("common.cancel")}</AlertDialogCancel>
          <AlertDialogAction onClick={confirm} disabled={undo.isPending}>
            {t("applications.undoLast")}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
