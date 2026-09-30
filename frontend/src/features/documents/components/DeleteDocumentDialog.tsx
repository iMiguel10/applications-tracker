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
import { useDeleteDocument } from "../hooks/mutations/useDeleteDocument";
import type { LibraryDocument } from "../types/Document";

interface DeleteDocumentDialogProps {
  document: LibraryDocument | null;
  onOpenChange: (open: boolean) => void;
}

/** Borrado definitivo: la fila y el PDF. Es lo que libera espacio; archivar no. */
export function DeleteDocumentDialog({ document, onOpenChange }: DeleteDocumentDialogProps) {
  const { t } = useTranslation();
  const remove = useDeleteDocument();

  const confirm = () => {
    if (!document) return;
    remove.mutate(document.id, {
      onSuccess: () => {
        toast.success(t("documents.deleted"));
        onOpenChange(false);
      },
      onError: (error) => toast.error(t(errorMessageKey(error), errorMessageParams(error))),
    });
  };

  return (
    <AlertDialog open={document !== null} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{t("documents.deleteTitle")}</AlertDialogTitle>
          <AlertDialogDescription>
            {t("documents.deleteConfirm", { name: document?.name })}
          </AlertDialogDescription>
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
