import { Briefcase, Download, Plus, SearchX } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import { toast } from "sonner";

import { useDocumentTitle } from "@/shared/hooks/useDocumentTitle";
import { errorMessageKey, errorMessageParams } from "@/shared/lib/errors";
import { Button, buttonVariants } from "@/shared/components/ui/button";
import { Card, CardContent } from "@/shared/components/ui/card";
import { EmptyState } from "@/shared/components/common/EmptyState";
import { ErrorState } from "@/shared/components/common/ErrorState";
import { Pagination } from "@/shared/components/common/Pagination";
import { TableSkeleton } from "@/shared/components/common/Skeletons";
import { ApplicationFilters } from "@/features/applications/components/ApplicationFilters";
import { ApplicationsTable } from "@/features/applications/components/ApplicationsTable";
import { useExportApplications } from "@/features/applications/hooks/mutations/useExportApplications";
import { useApplications } from "@/features/applications/hooks/queries/useApplications";
import {
  hasActiveFilters,
  parseListParams,
  serializeListParams,
  updateListParams,
} from "@/features/applications/lib/listParams";
import type { ApplicationListParams } from "@/features/applications/types/Application";

export function ApplicationsPage() {
  const { t } = useTranslation();
  useDocumentTitle(t("applications.title"));
  // Filtros, orden y página viven en la URL (decisión A16): la URL es el estado.
  const [searchParams, setSearchParams] = useSearchParams();
  const params = parseListParams(searchParams);
  const { data, isLoading, isError, isFetching, refetch } = useApplications(params);
  const exportCsv = useExportApplications();

  const change = (changes: Partial<ApplicationListParams>) =>
    setSearchParams(serializeListParams(updateListParams(params, changes)));

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold">{t("applications.title")}</h1>
        <div className="flex gap-2">
          <Button
            variant="outline"
            disabled={exportCsv.isPending}
            onClick={() =>
              exportCsv.mutate(undefined, {
                onError: (error) => toast.error(t(errorMessageKey(error), errorMessageParams(error))),
              })
            }
          >
            <Download />
            {t("applications.export")}
          </Button>
          <Link to="/applications/new" className={buttonVariants()}>
            <Plus />
            {t("applications.new")}
          </Link>
        </div>
      </div>

      <ApplicationFilters params={params} onChange={change} />

      {isLoading && <TableSkeleton columns={5} />}
      {isError && <ErrorState onRetry={() => refetch()} retrying={isFetching} />}
      {data &&
        data.total === 0 &&
        (hasActiveFilters(params) ? (
          // Sin acción propia: la barra de filtros ya muestra "Quitar filtros" justo encima.
          <EmptyState
            icon={SearchX}
            title={t("common.noResultsTitle")}
            description={t("common.noResults")}
          />
        ) : (
          <EmptyState
            icon={Briefcase}
            title={t("applications.emptyTitle")}
            description={t("applications.emptyDescription")}
            action={
              <Link to="/applications/new" className={buttonVariants()}>
                <Plus />
                {t("applications.new")}
              </Link>
            }
          />
        ))}
      {data && data.total > 0 && (
        <>
          <Card className="py-0">
            <CardContent className="px-0">
              <ApplicationsTable applications={data.items} />
            </CardContent>
          </Card>
          <Pagination
            page={data.page}
            pages={data.pages}
            total={data.total}
            onPageChange={(page) => change({ page })}
          />
        </>
      )}
    </div>
  );
}
