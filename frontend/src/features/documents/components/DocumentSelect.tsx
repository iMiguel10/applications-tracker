import { useState } from "react";
import { Upload } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { FieldValues, Path, PathValue, UseFormReturn } from "react-hook-form";

import { Button } from "@/shared/components/ui/button";
import { FormSelect } from "@/shared/components/form";
import { useDocuments } from "../hooks/queries/useDocuments";
import type { DocumentKind, DocumentSummary, LibraryDocument } from "../types/Document";
import { UploadDocumentDialog } from "./UploadDocumentDialog";

// La biblioteca tiene como mucho 100 documentos por defecto (límite de la cuenta):
// una página basta en la práctica. Si una cuenta tuviera más, faltarían los más
// antiguos, que se pueden elegir después de desarchivar o renombrar alguno.
const OPTIONS_LIMIT = 100;

interface DocumentSelectProps<T extends FieldValues> {
  form: UseFormReturn<T>;
  name: Path<T>;
  label: string;
  kind: DocumentKind;
  /** El que ya tiene la solicitud: se ofrece aunque esté archivado (RF-93). */
  current?: DocumentSummary | null;
}

/**
 * Elegir de la biblioteca el CV o la carta enviados en una solicitud (RF-28), o
 * subirlo en el momento: **Subir nuevo** abre la subida con el tipo fijado y deja
 * elegido el documento subido.
 */
export function DocumentSelect<T extends FieldValues>({
  form,
  name,
  label,
  kind,
  current,
}: DocumentSelectProps<T>) {
  const { t } = useTranslation();
  const { data } = useDocuments({ page: 1, limit: OPTIONS_LIMIT, kind, archived: false });
  const [uploadOpen, setUploadOpen] = useState(false);
  // El recién subido, hasta que llegue en el listado (la consulta se refresca sola).
  const [uploaded, setUploaded] = useState<LibraryDocument | null>(null);

  // Solo los que tienen PDF: uno que se está generando o que falló no se envió.
  const options = (data?.items ?? [])
    .filter((document) => document.status === "ready")
    .map((document) => ({
    value: document.id,
    label: document.name,
  }));
  if (uploaded && !options.some((option) => option.value === uploaded.id)) {
    options.unshift({ value: uploaded.id, label: uploaded.name });
  }
  if (current && !options.some((option) => option.value === current.id)) {
    options.push({
      value: current.id,
      label: `${current.name} (${t("documents.archivedBadge").toLowerCase()})`,
    });
  }

  const onUploaded = (document: LibraryDocument) => {
    setUploaded(document);
    form.setValue(name, document.id as PathValue<T, Path<T>>, {
      shouldDirty: true,
      shouldValidate: true,
    });
  };

  return (
    <div className="grid gap-2">
      <FormSelect
        form={form}
        name={name}
        label={label}
        options={options}
        emptyLabel={t("documents.none")}
      />
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="justify-self-start"
        onClick={() => setUploadOpen(true)}
      >
        <Upload />
        {t(`documents.upload.newKind.${kind}`)}
      </Button>
      <UploadDocumentDialog
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        kind={kind}
        onUploaded={onUploaded}
      />
    </div>
  );
}
