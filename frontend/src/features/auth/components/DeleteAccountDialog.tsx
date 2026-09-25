import { useId, useState } from "react";
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
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { useDeleteAccount } from "../hooks/mutations/useDeleteAccount";

interface DeleteAccountDialogProps {
  email: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/** Borrado irreversible: se confirma escribiendo el email de la cuenta, no con un
 * simple clic, para que no pueda hacerse por accidente. */
export function DeleteAccountDialog({ email, open, onOpenChange }: DeleteAccountDialogProps) {
  const { t } = useTranslation();
  const inputId = useId();
  const [typed, setTyped] = useState("");
  const remove = useDeleteAccount();

  const matches = typed.trim().toLowerCase() === email.toLowerCase();

  const changeOpen = (next: boolean) => {
    if (remove.isPending) return;
    if (!next) setTyped("");
    onOpenChange(next);
  };

  const confirm = () =>
    remove.mutate(undefined, {
      onSuccess: () => toast.success(t("account.delete.deletedToast")),
      onError: (error) => toast.error(t(errorMessageKey(error), errorMessageParams(error))),
    });

  return (
    <AlertDialog open={open} onOpenChange={changeOpen}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{t("account.delete.dialogTitle")}</AlertDialogTitle>
          <AlertDialogDescription>{t("account.delete.dialogDescription")}</AlertDialogDescription>
        </AlertDialogHeader>
        <div className="grid gap-2">
          <Label htmlFor={inputId}>{t("account.delete.confirmLabel", { email })}</Label>
          <Input
            id={inputId}
            type="email"
            autoComplete="off"
            value={typed}
            onChange={(event) => setTyped(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && matches && !remove.isPending) confirm();
            }}
          />
        </div>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={remove.isPending}>{t("common.cancel")}</AlertDialogCancel>
          <AlertDialogAction
            variant="destructive"
            onClick={confirm}
            disabled={!matches || remove.isPending}
          >
            {t("account.delete.confirmButton")}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
