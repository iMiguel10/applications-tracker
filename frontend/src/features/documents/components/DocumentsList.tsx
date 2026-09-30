import { useState } from "react";
import { Download, Eye, FileText } from "lucide-react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { errorMessageKey, errorMessageParams } from "@/shared/lib/errors";
import { formatBytes, formatDateTime } from "@/shared/lib/format";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { useDownloadDocument } from "../hooks/mutations/useDownloadDocument";
import type { LibraryDocument } from "../types/Document";
import { DocumentViewerDialog } from "./DocumentViewerDialog";

interface DocumentsListProps {
  documents: LibraryDocument[];
}

export function DocumentsList({ documents }: DocumentsListProps) {
  const { t, i18n } = useTranslation();
  const download = useDownloadDocument();
  const [viewing, setViewing] = useState<LibraryDocument | null>(null);

  const onDownload = (document: LibraryDocument) =>
    download.mutate(document, {
      onError: (error) => toast.error(t(errorMessageKey(error), errorMessageParams(error))),
    });

  return (
    <>
      <ul className="grid gap-2">
        {documents.map((document) => {
          const ready = document.status === "ready";
          return (
            <li
              key={document.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-card p-3"
            >
              <div className="flex min-w-0 flex-1 items-start gap-3">
                <FileText className="mt-0.5 size-5 shrink-0 text-muted-foreground" aria-hidden />
                <div className="grid min-w-0 gap-1">
                  {ready ? (
                    <button
                      type="button"
                      onClick={() => setViewing(document)}
                      className="truncate text-left font-medium underline-offset-2 hover:underline"
                      title={document.name}
                    >
                      {document.name}
                    </button>
                  ) : (
                    <span className="truncate font-medium" title={document.name}>
                      {document.name}
                    </span>
                  )}
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">
                    <Badge variant="secondary">{t(`documents.kinds.${document.kind}`)}</Badge>
                    <span>{t(`documents.origins.${document.origin}`)}</span>
                    {document.size_bytes !== null && (
                      <span className="tabular-nums">
                        {formatBytes(document.size_bytes, i18n.language)}
                      </span>
                    )}
                    <span>{formatDateTime(document.created_at, i18n.language)}</span>
                  </div>
                </div>
              </div>
              {ready && (
                <div className="flex gap-1">
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    aria-label={t("documents.viewNamed", { name: document.name })}
                    title={t("documents.view")}
                    onClick={() => setViewing(document)}
                  >
                    <Eye />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    aria-label={t("documents.downloadNamed", { name: document.name })}
                    title={t("documents.download")}
                    disabled={download.isPending && download.variables?.id === document.id}
                    onClick={() => onDownload(document)}
                  >
                    <Download />
                  </Button>
                </div>
              )}
            </li>
          );
        })}
      </ul>
      <DocumentViewerDialog document={viewing} onClose={() => setViewing(null)} />
    </>
  );
}
