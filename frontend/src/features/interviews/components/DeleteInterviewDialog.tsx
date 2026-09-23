import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { errorMessageKey } from "@/shared/lib/errors";
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
import { useDeleteInterview } from "../hooks/mutations/useDeleteInterview";

interface DeleteInterviewDialogProps {
  applicationId: string;
  interviewId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function DeleteInterviewDialog({
  applicationId,
  interviewId,
  open,
  onOpenChange,
}: DeleteInterviewDialogProps) {
  const { t } = useTranslation();
  const remove = useDeleteInterview(applicationId);

  const confirm = () =>
    remove.mutate(interviewId, {
      onSuccess: () => {
        toast.success(t("interviews.deleted"));
        onOpenChange(false);
      },
      onError: (error) => toast.error(t(errorMessageKey(error))),
    });

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{t("interviews.deleteTitle")}</AlertDialogTitle>
          <AlertDialogDescription>{t("interviews.deleteConfirm")}</AlertDialogDescription>
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
