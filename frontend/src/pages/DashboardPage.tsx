import { Plus, Sparkles } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { useDocumentTitle } from "@/shared/hooks/useDocumentTitle";
import { buttonVariants } from "@/shared/components/ui/button";
import { EmptyState } from "@/shared/components/common/EmptyState";
import { ErrorState } from "@/shared/components/common/ErrorState";
import { DashboardSkeleton } from "@/shared/components/common/Skeletons";
import { PendingRemindersWidget } from "@/features/dashboard/components/PendingRemindersWidget";
import { ResponseRateCard } from "@/features/dashboard/components/ResponseRateCard";
import { StaleApplicationsWidget } from "@/features/dashboard/components/StaleApplicationsWidget";
import { StatusBreakdownCard } from "@/features/dashboard/components/StatusBreakdownCard";
import { UpcomingInterviewsWidget } from "@/features/dashboard/components/UpcomingInterviewsWidget";
import { WeeklyApplicationsChart } from "@/features/dashboard/components/WeeklyApplicationsChart";
import { useDashboard } from "@/features/dashboard/hooks/queries/useDashboard";
import type { Dashboard } from "@/features/dashboard/types/Dashboard";

/** Sin nada que contar, seis tarjetas a cero no dicen nada: mejor invitar a empezar.
 * Las archivadas no cuentan en `status_counts`, por eso se miran también el resto de
 * listas antes de dar al usuario por "nuevo". */
function isBlank(data: Dashboard) {
  return (
    data.status_counts.every(({ count }) => count === 0) &&
    data.applications_per_week.every(({ count }) => count === 0) &&
    data.upcoming_interviews_total === 0 &&
    data.pending_reminders_total === 0
  );
}

export function DashboardPage() {
  const { t } = useTranslation();
  useDocumentTitle(t("dashboard.title"));
  const { data, isLoading, isError, isFetching, refetch } = useDashboard();

  return (
    <div className="grid gap-6">
      <h1 className="text-2xl font-semibold">{t("dashboard.title")}</h1>

      {isLoading && <DashboardSkeleton />}
      {isError && <ErrorState onRetry={() => refetch()} retrying={isFetching} />}

      {data && isBlank(data) && (
        <EmptyState
          icon={Sparkles}
          title={t("dashboard.welcome.title")}
          description={t("dashboard.welcome.description")}
          action={
            <Link to="/applications/new" className={buttonVariants()}>
              <Plus />
              {t("applications.new")}
            </Link>
          }
        />
      )}

      {data && !isBlank(data) && (
        <>
          <div className="grid gap-4 lg:grid-cols-[2fr_2fr_1fr]">
            <StatusBreakdownCard statusCounts={data.status_counts} />
            <WeeklyApplicationsChart applicationsPerWeek={data.applications_per_week} />
            <ResponseRateCard responseRate={data.response_rate} />
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <UpcomingInterviewsWidget
              interviews={data.upcoming_interviews}
              total={data.upcoming_interviews_total}
            />
            <PendingRemindersWidget
              reminders={data.pending_reminders}
              total={data.pending_reminders_total}
            />
            <StaleApplicationsWidget
              applications={data.stale_applications}
              total={data.stale_applications_total}
              afterDays={data.stale_after_days}
            />
          </div>
        </>
      )}
    </div>
  );
}
