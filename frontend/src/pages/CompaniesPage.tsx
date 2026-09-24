import { useState } from "react";
import { Building2, Plus, SearchX } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";

import { useDocumentTitle } from "@/shared/hooks/useDocumentTitle";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent } from "@/shared/components/ui/card";
import { EmptyState } from "@/shared/components/common/EmptyState";
import { ErrorState } from "@/shared/components/common/ErrorState";
import { Pagination } from "@/shared/components/common/Pagination";
import { TableSkeleton } from "@/shared/components/common/Skeletons";
import { SearchInput } from "@/shared/components/common/SearchInput";
import { CompaniesTable } from "@/features/companies/components/CompaniesTable";
import { CompanyFormDialog } from "@/features/companies/components/CompanyFormDialog";
import { DeleteCompanyDialog } from "@/features/companies/components/DeleteCompanyDialog";
import { useCompanies } from "@/features/companies/hooks/queries/useCompanies";
import type { Company } from "@/features/companies/types/Company";

const PAGE_SIZE = 20;

export function CompaniesPage() {
  const { t } = useTranslation();
  useDocumentTitle(t("companies.title"));
  // Búsqueda y página en la URL (decisión A16): sobreviven a recargar y al botón atrás.
  const [searchParams, setSearchParams] = useSearchParams();
  const q = searchParams.get("q") ?? "";
  const page = Math.max(1, Number(searchParams.get("page")) || 1);

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Company | null>(null);
  const [deleting, setDeleting] = useState<Company | null>(null);

  const { data, isLoading, isError, isFetching, refetch } = useCompanies({
    page,
    limit: PAGE_SIZE,
    q: q || undefined,
  });

  const setParams = (next: { q?: string; page?: number }) => {
    const params = new URLSearchParams(searchParams);
    if (next.q !== undefined) {
      if (next.q) params.set("q", next.q);
      else params.delete("q");
      params.delete("page"); // una búsqueda nueva empieza en la primera página
    }
    if (next.page !== undefined) {
      if (next.page > 1) params.set("page", String(next.page));
      else params.delete("page");
    }
    setSearchParams(params);
  };

  const openCreate = () => {
    setEditing(null);
    setFormOpen(true);
  };
  const openEdit = (company: Company) => {
    setEditing(company);
    setFormOpen(true);
  };

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold">{t("companies.title")}</h1>
        <Button onClick={openCreate}>
          <Plus />
          {t("companies.new")}
        </Button>
      </div>

      <SearchInput
        value={q}
        onChange={(value) => setParams({ q: value })}
        placeholder={t("companies.searchPlaceholder")}
      />

      {isLoading && <TableSkeleton columns={4} />}
      {isError && <ErrorState onRetry={() => refetch()} retrying={isFetching} />}
      {data &&
        data.total === 0 &&
        (q ? (
          <EmptyState
            icon={SearchX}
            title={t("common.noResultsTitle")}
            description={t("companies.noSearchResults", { q })}
          />
        ) : (
          <EmptyState
            icon={Building2}
            title={t("companies.emptyTitle")}
            description={t("companies.emptyDescription")}
            action={
              <Button onClick={openCreate}>
                <Plus />
                {t("companies.new")}
              </Button>
            }
          />
        ))}
      {data && data.total > 0 && (
        <>
          <Card className="py-0">
            <CardContent className="px-0">
              <CompaniesTable companies={data.items} onEdit={openEdit} onDelete={setDeleting} />
            </CardContent>
          </Card>
          <Pagination
            page={data.page}
            pages={data.pages}
            total={data.total}
            onPageChange={(next) => setParams({ page: next })}
          />
        </>
      )}

      <CompanyFormDialog open={formOpen} onOpenChange={setFormOpen} company={editing} />
      <DeleteCompanyDialog company={deleting} onOpenChange={(open) => !open && setDeleting(null)} />
    </div>
  );
}
