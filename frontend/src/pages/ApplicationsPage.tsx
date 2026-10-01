import { Briefcase, Columns3, Download, List, Plus, SearchX } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import { toast } from "sonner";

import { useDocumentTitle } from "@/shared/hooks/useDocumentTitle";
import { errorMessageKey, errorMessageParams } from "@/shared/lib/errors";
import { Button, buttonVariants } from "@/shared/components/ui/button";
import { Card, CardContent } from "@/shared/components/ui/card";
import { EmptyState } from "@/shared/components/common/EmptyState";
import { ViewToggle } from "@/shared/components/common/ViewToggle";
import { ErrorState } from "@/shared/components/common/ErrorState";
import { Pagination } from "@/shared/components/common/Pagination";
import { ListSkeleton, TableSkeleton } from "@/shared/components/common/Skeletons";
import { ApplicationFilters } from "@/features/applications/components/ApplicationFilters";
import { ApplicationsTable } from "@/features/applications/components/ApplicationsTable";
import { useExportApplications } from "@/features/applications/hooks/mutations/useExportApplications";
import { useApplications } from "@/features/applications/hooks/queries/useApplications";
import {
  boardViewParams,
  hasActiveFilters,
  parseListParams,
  serializeListParams,
  updateListParams,
} from "@/features/applications/lib/listParams";
import type {
  ApplicationListParams,
  ApplicationStatus,
} from "@/features/applications/types/Application";
import { ApplicationBoard } from "@/features/board/components/ApplicationBoard";
import { useBoard } from "@/features/board/hooks/queries/useBoard";
import { boardFilters } from "@/features/board/services/board.service";

export function ApplicationsPage() {
  const { t } = useTranslation();
  useDocumentTitle(t("applications.title"));
  // Filtros, orden y página viven en la URL (decisión A16): la URL es el estado.
  const [searchParams, setSearchParams] = useSearchParams();
  // Lista o tablero (RF-122): la vista va en la URL con los filtros, que comparten.
  const board = searchParams.get("view") === "board";
  const listParams = parseListParams(searchParams);
  const params = board ? boardViewParams(listParams) : listParams;
  const { data, isLoading, isError, isFetching, refetch } = useApplications(params, {
    enabled: !board,
  });
  const filters = boardFilters(params);
  const boardQuery = useBoard(filters, { enabled: board });
  const exportCsv = useExportApplications();

  const withView = (search: URLSearchParams, toBoard: boolean) => {
    if (toBoard) search.set("view", "board");
    return search;
  };
  const change = (changes: Partial<ApplicationListParams>) =>
    setSearchParams(withView(serializeListParams(updateListParams(params, changes)), board));
  // Al pasar al tablero, la URL pierde archivado y orden, que allí no se ven.
  const setView = (toBoard: boolean) =>
    setSearchParams(
      withView(
        serializeListParams(updateListParams(toBoard ? boardViewParams(params) : params, {})),
        toBoard,
      ),
    );
  // "y N más" de una columna: el listado con los mismos filtros y ese estado.
  const listHref = (status: ApplicationStatus) =>
    `/applications?${serializeListParams(updateListParams(params, { status: [status] }))}`;
  const boardTotal = boardQuery.data?.columns.reduce((sum, column) => sum + column.total, 0);

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        {/* El selector va junto al título y no junto a los filtros: en el tablero hay
            menos filtros y, a su lado, cambiaría de sitio al cambiar de vista. */}
        <div className="flex flex-wrap items-center gap-4">
          <h1 className="text-2xl font-semibold">{t("applications.title")}</h1>
          <ViewToggle
            label={t("board.view")}
            options={[
              { value: "list", label: t("board.viewList"), icon: List },
              { value: "board", label: t("board.viewBoard"), icon: Columns3 },
            ]}
            value={board ? "board" : "list"}
            onChange={(view) => setView(view === "board")}
          />
        </div>
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

      <ApplicationFilters params={params} onChange={change} board={board} />

      {board && boardQuery.isLoading && <ListSkeleton rows={3} />}
      {board && boardQuery.isError && (
        <ErrorState onRetry={() => boardQuery.refetch()} retrying={boardQuery.isFetching} />
      )}
      {board &&
        boardTotal === 0 &&
        (hasActiveFilters(params) ? (
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
      {board && boardQuery.data && !!boardTotal && (
        <ApplicationBoard board={boardQuery.data} filters={filters} listHref={listHref} />
      )}

      {!board && isLoading && <TableSkeleton columns={5} />}
      {!board && isError && <ErrorState onRetry={() => refetch()} retrying={isFetching} />}
      {!board &&
        data &&
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
      {!board && data && data.total > 0 && (
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
