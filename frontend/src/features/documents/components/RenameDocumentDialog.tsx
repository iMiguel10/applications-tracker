import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { z } from "zod";

import { errorMessageKey, errorMessageParams } from "@/shared/lib/errors";
import { FormActions, FormInput } from "@/shared/components/form";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/shared/components/ui/dialog";
import { useRenameDocument } from "../hooks/mutations/useRenameDocument";
import type { LibraryDocument } from "../types/Document";

const renameSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "documents.validation.nameRequired")
    .max(200, "common.validation.tooLong"),
});

type RenameFormValues = z.infer<typeof renameSchema>;

interface RenameDocumentDialogProps {
  document: LibraryDocument | null;
  onOpenChange: (open: boolean) => void;
}

export function RenameDocumentDialog({ document, onOpenChange }: RenameDocumentDialogProps) {
  const { t } = useTranslation();
  const rename = useRenameDocument();
  const form = useForm<RenameFormValues>({
    resolver: zodResolver(renameSchema),
    defaultValues: { name: "" },
  });

  useEffect(() => {
    if (document) form.reset({ name: document.name });
  }, [document, form]);

  const onSubmit = ({ name }: RenameFormValues) => {
    if (!document) return;
    rename.mutate(
      { id: document.id, name },
      {
        onSuccess: () => {
          toast.success(t("documents.renamed"));
          onOpenChange(false);
        },
        onError: (error) => toast.error(t(errorMessageKey(error), errorMessageParams(error))),
      },
    );
  };

  return (
    <Dialog open={document !== null} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("documents.renameTitle")}</DialogTitle>
        </DialogHeader>
        <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-4" noValidate>
          <FormInput form={form} name="name" label={t("documents.fields.name")} />
          <FormActions
            loading={rename.isPending}
            submitLabel={t("common.save")}
            cancelLabel={t("common.cancel")}
            onCancel={() => onOpenChange(false)}
          />
        </form>
      </DialogContent>
    </Dialog>
  );
}
