import { useState } from "react";
import { Archive, ArchiveRestore, Download, Eye, FileText, Pencil, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { errorMessageKey, errorMessageParams } from "@/shared/lib/errors";
import { formatBytes, formatDateTime } from "@/shared/lib/format";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { useDownloadDocument } from "../hooks/mutations/useDownloadDocument";
import { useSetDocumentArchived } from "../hooks/mutations/useSetDocumentArchived";
import type { DocumentListItem } from "../types/Document";
import { DeleteDocumentDialog } from "./DeleteDocumentDialog";
import { DocumentViewerDialog } from "./DocumentViewerDialog";
import { RenameDocumentDialog } from "./RenameDocumentDialog";

interface DocumentsListProps {
  documents: DocumentListItem[];
}

export function DocumentsList({ documents }: DocumentsListProps) {
  const { t, i18n } = useTranslation();
  const download = useDownloadDocument();
  const setArchived = useSetDocumentArchived();
  const [viewing, setViewing] = useState<DocumentListItem | null>(null);
  const [renaming, setRenaming] = useState<DocumentListItem | null>(null);
  const [deleting, setDeleting] = useState<DocumentListItem | null>(null);

  const onError = (error: Error) => toast.error(t(errorMessageKey(error), errorMessageParams(error)));

  const toggleArchived = (document: DocumentListItem) => {
    const archived = document.archived_at === null;
    setArchived.mutate(
      { id: document.id, archived },
      {
        onSuccess: () =>
          toast.success(t(archived ? "documents.archived" : "documents.unarchived")),
        onError,
      },
    );
  };

  return (
    <>
      <ul className="grid gap-2">
        {documents.map((document) => {
          const ready = document.status === "ready";
          const isArchived = document.archived_at !== null;
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
                    {isArchived && <Badge variant="outline">{t("documents.archivedBadge")}</Badge>}
                    {document.applications_count > 0 &&
                      (ready ? (
                        <button
                          type="button"
                          onClick={() => setViewing(document)}
                          title={t("documents.usage.seeWhere")}
                          className="rounded-full focus-visible:outline-2 focus-visible:outline-ring"
                        >
                          <Badge variant="outline" className="cursor-pointer hover:bg-muted">
                            {t("documents.usage.sentIn", { count: document.applications_count })}
                          </Badge>
                        </button>
                      ) : (
                        <Badge variant="outline">
                          {t("documents.usage.sentIn", { count: document.applications_count })}
                        </Badge>
                      ))}
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
              <div className="flex flex-wrap gap-1">
                {ready && (
                  <>
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
                      onClick={() => download.mutate(document, { onError })}
                    >
                      <Download />
                    </Button>
                  </>
                )}
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label={t("documents.renameNamed", { name: document.name })}
                  title={t("documents.rename")}
                  onClick={() => setRenaming(document)}
                >
                  <Pencil />
                </Button>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label={t(isArchived ? "documents.unarchiveNamed" : "documents.archiveNamed", {
                    name: document.name,
                  })}
                  title={t(isArchived ? "documents.unarchive" : "documents.archive")}
                  disabled={setArchived.isPending && setArchived.variables?.id === document.id}
                  onClick={() => toggleArchived(document)}
                >
                  {isArchived ? <ArchiveRestore /> : <Archive />}
                </Button>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  className="hover:bg-destructive/10 hover:text-destructive"
                  aria-label={t("documents.deleteNamed", { name: document.name })}
                  title={t("common.delete")}
                  onClick={() => setDeleting(document)}
                >
                  <Trash2 />
                </Button>
              </div>
            </li>
          );
        })}
      </ul>
      <DocumentViewerDialog document={viewing} onClose={() => setViewing(null)} />
      <RenameDocumentDialog document={renaming} onOpenChange={(open) => !open && setRenaming(null)} />
      <DeleteDocumentDialog document={deleting} onOpenChange={(open) => !open && setDeleting(null)} />
    </>
  );
}
