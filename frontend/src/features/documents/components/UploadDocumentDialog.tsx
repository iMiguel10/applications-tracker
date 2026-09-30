import { useEffect, useMemo } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { errorMessageKey, errorMessageParams } from "@/shared/lib/errors";
import { formatBytes } from "@/shared/lib/format";
import { FormActions, FormFileInput, FormSelect } from "@/shared/components/form";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import { useMeta } from "@/features/meta/hooks/queries/useMeta";
import { LimitWarning } from "@/features/usage/components/LimitWarning";
import { useUsage } from "@/features/usage/hooks/queries/useUsage";
import { useUploadDocument } from "../hooks/mutations/useUploadDocument";
import { emptyUploadForm, uploadSchema, type UploadFormValues } from "../schemas/upload.schema";
import { DOCUMENT_KINDS, type DocumentKind, type LibraryDocument } from "../types/Document";

// Mientras llega GET /meta: el valor por defecto de la API. La API decide igual.
const FALLBACK_MAX_BYTES = 5 * 1024 * 1024;

interface UploadDocumentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Tipo fijo (subir desde una solicitud, al lado de su selector): no se pregunta. */
  kind?: DocumentKind;
  /** Tras subirlo: p. ej. dejarlo elegido en el formulario de la solicitud. */
  onUploaded?: (document: LibraryDocument) => void;
}

export function UploadDocumentDialog({
  open,
  onOpenChange,
  kind: fixedKind,
  onUploaded,
}: UploadDocumentDialogProps) {
  const { t, i18n } = useTranslation();
  const upload = useUploadDocument();
  const { data: meta } = useMeta();
  const { data: usage } = useUsage();
  const maxBytes = meta?.max_document_bytes ?? FALLBACK_MAX_BYTES;
  const schema = useMemo(() => uploadSchema(maxBytes), [maxBytes]);

  const form = useForm<UploadFormValues>({
    resolver: zodResolver(schema),
    defaultValues: emptyUploadForm,
  });

  useEffect(() => {
    if (open) form.reset({ ...emptyUploadForm, kind: fixedKind ?? emptyUploadForm.kind });
  }, [open, form, fixedKind]);

  // RF-144: lo que queda de almacenamiento, donde se gasta.
  const storage = usage?.limits.find((limit) => limit.key === "storage_bytes");
  const hint = [
    t("documents.upload.maxSize", { size: formatBytes(maxBytes, i18n.language) }),
    storage?.remaining != null &&
      t("documents.upload.storageLeft", {
        size: formatBytes(storage.remaining, i18n.language),
      }),
  ]
    .filter(Boolean)
    .join(" ");

  const onSubmit = ({ kind, file }: UploadFormValues) => {
    if (!file) return;
    upload.mutate(
      { kind, file },
      {
        onSuccess: (document) => {
          toast.success(t("documents.upload.done"));
          onUploaded?.(document);
          onOpenChange(false);
        },
        onError: (error) => toast.error(t(errorMessageKey(error), errorMessageParams(error))),
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {t(fixedKind ? `documents.upload.titleKind.${fixedKind}` : "documents.upload.title")}
          </DialogTitle>
          <DialogDescription>{t("documents.upload.description")}</DialogDescription>
        </DialogHeader>
        <form
          // stopPropagation: este diálogo se abre también DENTRO del formulario de una
          // solicitud. Aunque se pinte en un portal, en React el submit sube por el
          // árbol de componentes y enviaría también la solicitud.
          onSubmit={(event) => {
            event.stopPropagation();
            void form.handleSubmit(onSubmit)(event);
          }}
          className="grid gap-4"
          noValidate
        >
          <LimitWarning limitKey="documents" />
          <LimitWarning limitKey="storage_bytes" />
          {!fixedKind && (
            <FormSelect
              form={form}
              name="kind"
              label={t("documents.fields.kind")}
              options={DOCUMENT_KINDS.map((kind) => ({
                value: kind,
                label: t(`documents.kinds.${kind}`),
              }))}
            />
          )}
          <FormFileInput
            form={form}
            name="file"
            label={t("documents.fields.file")}
            accept="application/pdf,.pdf"
            hint={hint}
          />
          <FormActions
            loading={upload.isPending}
            submitLabel={t("documents.upload.submit")}
            cancelLabel={t("common.cancel")}
            onCancel={() => onOpenChange(false)}
          />
        </form>
      </DialogContent>
    </Dialog>
  );
}
