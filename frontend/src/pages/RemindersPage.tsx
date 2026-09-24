import { useState } from "react";
import { BellRing, Plus, SearchX } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";

import { useDocumentTitle } from "@/shared/hooks/useDocumentTitle";
import { Button } from "@/shared/components/ui/button";
import { EmptyState } from "@/shared/components/common/EmptyState";
import { ErrorState } from "@/shared/components/common/ErrorState";
import { Pagination } from "@/shared/components/common/Pagination";
import { ListSkeleton } from "@/shared/components/common/Skeletons";
import { ReminderFormDialog } from "@/features/reminders/components/ReminderFormDialog";
import { RemindersFilters } from "@/features/reminders/components/RemindersFilters";
import { RemindersList } from "@/features/reminders/components/RemindersList";
import { useReminders } from "@/features/reminders/hooks/queries/useReminders";
import {
  DEFAULT_LIST_PARAMS,
  parseListParams,
  serializeListParams,
  updateListParams,
} from "@/features/reminders/lib/listParams";
import type { ReminderListParams } from "@/features/reminders/types/Reminder";

export function RemindersPage() {
  const { t } = useTranslation();
  useDocumentTitle(t("reminders.title"));
  // Filtros y página en la URL (decisión A16), igual que el listado de solicitudes.
  const [searchParams, setSearchParams] = useSearchParams();
  const params = parseListParams(searchParams);
  const { data, isLoading, isError, isFetching, refetch } = useReminders(params);
  const [formOpen, setFormOpen] = useState(false);

  const change = (changes: Partial<ReminderListParams>) =>
    setSearchParams(serializeListParams(updateListParams(params, changes)));

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold">{t("reminders.title")}</h1>
        <Button onClick={() => setFormOpen(true)}>
          <Plus />
          {t("reminders.new")}
        </Button>
      </div>

      <RemindersFilters params={params} onChange={change} />

      {isLoading && <ListSkeleton rows={4} />}
      {isError && <ErrorState onRetry={() => refetch()} retrying={isFetching} />}
      {data &&
        data.total === 0 &&
        (params.status === DEFAULT_LIST_PARAMS.status ? (
          <EmptyState
            icon={BellRing}
            title={t("reminders.emptyPendingTitle")}
            description={t("reminders.emptyPendingDescription")}
            action={
              <Button onClick={() => setFormOpen(true)}>
                <Plus />
                {t("reminders.new")}
              </Button>
            }
          />
        ) : (
          <EmptyState
            icon={SearchX}
            title={t("common.noResultsTitle")}
            description={t("reminders.emptyList")}
          />
        ))}
      {data && data.total > 0 && (
        <>
          <RemindersList reminders={data.items} />
          <Pagination
            page={data.page}
            pages={data.pages}
            total={data.total}
            onPageChange={(page) => change({ page })}
          />
        </>
      )}

      <ReminderFormDialog open={formOpen} onOpenChange={setFormOpen} />
    </div>
  );
}
