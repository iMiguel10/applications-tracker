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
import { useDeleteApplication } from "../hooks/mutations/useDeleteApplication";
import type { Application } from "../types/Application";

interface DeleteApplicationDialogProps {
  application: Application;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDeleted: () => void;
}

export function DeleteApplicationDialog({
  application,
  open,
  onOpenChange,
  onDeleted,
}: DeleteApplicationDialogProps) {
  const { t } = useTranslation();
  const remove = useDeleteApplication();

  const confirm = () =>
    remove.mutate(application.id, {
      onSuccess: () => {
        toast.success(t("applications.deleted"));
        onDeleted();
      },
      onError: (error) => toast.error(t(errorMessageKey(error))),
    });

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{t("applications.deleteTitle")}</AlertDialogTitle>
          <AlertDialogDescription>{t("applications.deleteConfirm")}</AlertDialogDescription>
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
