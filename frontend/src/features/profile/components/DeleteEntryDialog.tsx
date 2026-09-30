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
import { useDeleteEntry } from "../hooks/mutations/useDeleteEntry";
import type { ProfileEntry } from "../types/ProfileEntry";

type Props = {
  entry: ProfileEntry | null;
  onOpenChange: (open: boolean) => void;
};

export function DeleteEntryDialog({ entry, onOpenChange }: Props) {
  const { t } = useTranslation();
  const remove = useDeleteEntry();

  const confirm = () => {
    if (!entry) return;
    remove.mutate(entry.id, {
      onSuccess: () => {
        toast.success(t("profile.entries.deleted"));
        onOpenChange(false);
      },
      onError: (error) => toast.error(t(errorMessageKey(error), errorMessageParams(error))),
    });
  };

  return (
    <AlertDialog open={!!entry} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>
            {t("profile.entries.deleteTitle", { title: entry?.title })}
          </AlertDialogTitle>
          <AlertDialogDescription>{t("profile.entries.deleteConfirm")}</AlertDialogDescription>
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
