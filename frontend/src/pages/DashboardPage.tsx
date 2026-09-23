import { useTranslation } from "react-i18next";

import { PendingRemindersWidget } from "@/features/dashboard/components/PendingRemindersWidget";
import { ResponseRateCard } from "@/features/dashboard/components/ResponseRateCard";
import { StaleApplicationsWidget } from "@/features/dashboard/components/StaleApplicationsWidget";
import { StatusBreakdownCard } from "@/features/dashboard/components/StatusBreakdownCard";
import { UpcomingInterviewsWidget } from "@/features/dashboard/components/UpcomingInterviewsWidget";
import { WeeklyApplicationsChart } from "@/features/dashboard/components/WeeklyApplicationsChart";
import { useDashboard } from "@/features/dashboard/hooks/queries/useDashboard";

export function DashboardPage() {
  const { t } = useTranslation();
  const { data, isLoading, isError } = useDashboard();

  return (
    <div className="grid gap-6">
      <h1 className="text-2xl font-semibold">{t("dashboard.title")}</h1>

      {isLoading && <p className="text-muted-foreground">{t("common.loading")}</p>}
      {isError && <p className="text-destructive">{t("errors.generic")}</p>}

      {data && (
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
