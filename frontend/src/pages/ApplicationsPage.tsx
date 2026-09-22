import { Plus } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";

import { buttonVariants } from "@/shared/components/ui/button";
import { Pagination } from "@/shared/components/common/Pagination";
import { ApplicationFilters } from "@/features/applications/components/ApplicationFilters";
import { ApplicationsTable } from "@/features/applications/components/ApplicationsTable";
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
  // Filtros, orden y página viven en la URL (decisión A16): la URL es el estado.
  const [searchParams, setSearchParams] = useSearchParams();
  const params = parseListParams(searchParams);
  const { data, isLoading, isError } = useApplications(params);

  const change = (changes: Partial<ApplicationListParams>) =>
    setSearchParams(serializeListParams(updateListParams(params, changes)));

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold">{t("applications.title")}</h1>
        <Link to="/applications/new" className={buttonVariants()}>
          <Plus />
          {t("applications.new")}
        </Link>
      </div>

      <ApplicationFilters params={params} onChange={change} />

      {isLoading && <p className="text-muted-foreground">{t("common.loading")}</p>}
      {isError && <p className="text-destructive">{t("errors.generic")}</p>}
      {data && data.total === 0 && (
        <p className="text-muted-foreground">
          {t(hasActiveFilters(params) ? "common.noResults" : "applications.empty")}
        </p>
      )}
      {data && data.total > 0 && (
        <>
          <ApplicationsTable applications={data.items} />
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
