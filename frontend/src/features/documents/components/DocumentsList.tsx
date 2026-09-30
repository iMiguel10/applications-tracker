import { FileText } from "lucide-react";
import { useTranslation } from "react-i18next";

import { formatBytes, formatDateTime } from "@/shared/lib/format";
import { Badge } from "@/shared/components/ui/badge";
import type { LibraryDocument } from "../types/Document";

interface DocumentsListProps {
  documents: LibraryDocument[];
}

export function DocumentsList({ documents }: DocumentsListProps) {
  const { t, i18n } = useTranslation();

  return (
    <ul className="grid gap-2">
      {documents.map((document) => (
        <li
          key={document.id}
          className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-card p-3"
        >
          <div className="flex min-w-0 items-start gap-3">
            <FileText className="mt-0.5 size-5 shrink-0 text-muted-foreground" aria-hidden />
            <div className="grid min-w-0 gap-1">
              <span className="truncate font-medium" title={document.name}>
                {document.name}
              </span>
              <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">
                <Badge variant="secondary">{t(`documents.kinds.${document.kind}`)}</Badge>
                <span>{t(`documents.origins.${document.origin}`)}</span>
                {document.size_bytes !== null && (
                  <span className="tabular-nums">{formatBytes(document.size_bytes, i18n.language)}</span>
                )}
                <span>{formatDateTime(document.created_at, i18n.language)}</span>
              </div>
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}
