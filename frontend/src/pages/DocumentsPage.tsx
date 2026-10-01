import { useState } from "react";
import { FilePlus2, FileText, SearchX, Upload } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";

import { useDocumentTitle } from "@/shared/hooks/useDocumentTitle";
import { Button } from "@/shared/components/ui/button";
import { EmptyState } from "@/shared/components/common/EmptyState";
import { ErrorState } from "@/shared/components/common/ErrorState";
import { Pagination } from "@/shared/components/common/Pagination";
import { ListSkeleton } from "@/shared/components/common/Skeletons";
import { DocumentsFilters } from "@/features/documents/components/DocumentsFilters";
import { DocumentsList } from "@/features/documents/components/DocumentsList";
import { GenerateCvDialog } from "@/features/documents/components/GenerateCvDialog";
import { UploadDocumentDialog } from "@/features/documents/components/UploadDocumentDialog";
import { useDocuments } from "@/features/documents/hooks/queries/useDocuments";
import {
  DEFAULT_LIST_PARAMS,
  parseListParams,
  serializeListParams,
  updateListParams,
} from "@/features/documents/lib/listParams";
import type { DocumentListParams } from "@/features/documents/types/Document";

/** Biblioteca de documentos (RF-90): los CVs y cartas en PDF de la cuenta. */
export function DocumentsPage() {
  const { t } = useTranslation();
  useDocumentTitle(t("documents.title"));
  // Filtros y página en la URL (decisión A16), como el resto de listados.
  const [searchParams, setSearchParams] = useSearchParams();
  const params = parseListParams(searchParams);
  const { data, isLoading, isError, isFetching, refetch } = useDocuments(params);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [generateOpen, setGenerateOpen] = useState(false);

  const change = (changes: Partial<DocumentListParams>) =>
    setSearchParams(serializeListParams(updateListParams(params, changes)));

  const uploadButton = (
    <Button onClick={() => setUploadOpen(true)}>
      <Upload />
      {t("documents.upload.open")}
    </Button>
  );

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="grid gap-1">
          <h1 className="text-2xl font-semibold">{t("documents.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("documents.subtitle")}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => setGenerateOpen(true)}>
            <FilePlus2 />
            {t("documents.generate.open")}
          </Button>
          {uploadButton}
        </div>
      </div>

      <DocumentsFilters params={params} onChange={change} />

      {isLoading && <ListSkeleton rows={4} />}
      {isError && <ErrorState onRetry={() => refetch()} retrying={isFetching} />}
      {data &&
        data.total === 0 &&
        (params.kind === DEFAULT_LIST_PARAMS.kind && !params.archived ? (
          <EmptyState
            icon={FileText}
            title={t("documents.emptyTitle")}
            description={t("documents.emptyDescription")}
            action={uploadButton}
          />
        ) : (
          <EmptyState
            icon={SearchX}
            title={t("common.noResultsTitle")}
            description={t(
              params.archived ? "documents.emptyArchived" : "documents.emptyFiltered",
            )}
          />
        ))}
      {data && data.total > 0 && (
        <>
          <DocumentsList documents={data.items} />
          <Pagination
            page={data.page}
            pages={data.pages}
            total={data.total}
            onPageChange={(page) => change({ page })}
          />
        </>
      )}

      <UploadDocumentDialog open={uploadOpen} onOpenChange={setUploadOpen} />
      <GenerateCvDialog open={generateOpen} onOpenChange={setGenerateOpen} />
    </div>
  );
}
