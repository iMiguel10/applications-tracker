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
import { useDeleteCompany } from "../hooks/mutations/useDeleteCompany";
import type { Company } from "../types/Company";

interface DeleteCompanyDialogProps {
  company: Company | null;
  onOpenChange: (open: boolean) => void;
}

export function DeleteCompanyDialog({ company, onOpenChange }: DeleteCompanyDialogProps) {
  const { t } = useTranslation();
  const remove = useDeleteCompany();
  // RF-12: con solicitudes no se puede borrar. Se avisa antes de intentarlo; si el
  // recuento estuviera desfasado, la API responde 409 company_in_use igualmente.
  const inUse = (company?.applications_count ?? 0) > 0;

  const confirm = () => {
    if (!company) return;
    remove.mutate(company.id, {
      onSuccess: () => {
        toast.success(t("companies.deleted"));
        onOpenChange(false);
      },
      onError: (error) => toast.error(t(errorMessageKey(error))),
    });
  };

  return (
    <AlertDialog open={!!company} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{t("companies.deleteTitle", { name: company?.name })}</AlertDialogTitle>
          <AlertDialogDescription>
            {inUse
              ? t("companies.deleteInUse", { count: company?.applications_count })
              : t("companies.deleteConfirm")}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>{t("common.cancel")}</AlertDialogCancel>
          {!inUse && (
            <AlertDialogAction variant="destructive" onClick={confirm} disabled={remove.isPending}>
              {t("common.delete")}
            </AlertDialogAction>
          )}
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
