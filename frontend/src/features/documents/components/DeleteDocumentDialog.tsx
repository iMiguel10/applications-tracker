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
import { useSetDocumentArchived } from "../hooks/mutations/useSetDocumentArchived";
import type { DocumentListItem } from "../types/Document";

interface DeleteDocumentDialogProps {
  document: DocumentListItem | null;
  onOpenChange: (open: boolean) => void;
}

/**
 * Borrado definitivo: la fila y el PDF. Es lo que libera espacio; archivar no.
 * Un documento enviado en alguna solicitud no se puede borrar (RF-93): en vez de
 * dejar que la API responda 409, el diálogo lo dice antes y ofrece archivarlo.
 */
export function DeleteDocumentDialog({ document, onOpenChange }: DeleteDocumentDialogProps) {
  const { t } = useTranslation();
  const remove = useDeleteDocument();
  const setArchived = useSetDocumentArchived();
  const inUse = (document?.applications_count ?? 0) > 0;
  const canArchive = inUse && document?.archived_at === null;

  const onError = (error: Error) => toast.error(t(errorMessageKey(error), errorMessageParams(error)));

  const confirm = () => {
    if (!document) return;
    if (inUse) {
      if (!canArchive) return onOpenChange(false);
      setArchived.mutate(
        { id: document.id, archived: true },
        {
          onSuccess: () => {
            toast.success(t("documents.archived"));
            onOpenChange(false);
          },
          onError,
        },
      );
      return;
    }
    remove.mutate(document.id, {
      onSuccess: () => {
        toast.success(t("documents.deleted"));
        onOpenChange(false);
      },
      onError,
    });
  };

  return (
    <AlertDialog open={document !== null} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>
            {t(inUse ? "documents.deleteInUseTitle" : "documents.deleteTitle")}
          </AlertDialogTitle>
          <AlertDialogDescription>
            {inUse
              ? t(canArchive ? "documents.deleteInUse" : "documents.deleteInUseArchived", {
                  name: document?.name,
                  count: document?.applications_count,
                })
              : t("documents.deleteConfirm", { name: document?.name })}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          {(!inUse || canArchive) && <AlertDialogCancel>{t("common.cancel")}</AlertDialogCancel>}
          <AlertDialogAction
            variant={inUse ? "default" : "destructive"}
            onClick={confirm}
            disabled={remove.isPending || setArchived.isPending}
          >
            {inUse ? t(canArchive ? "documents.archive" : "common.close") : t("common.delete")}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
