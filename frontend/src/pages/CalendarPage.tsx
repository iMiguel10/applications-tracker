import { CalendarDays, CalendarRange, ChevronLeft, ChevronRight } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";

import { useDocumentTitle } from "@/shared/hooks/useDocumentTitle";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/components/ui/button";
import { ErrorState } from "@/shared/components/common/ErrorState";
import { ListSkeleton } from "@/shared/components/common/Skeletons";
import { ViewToggle } from "@/shared/components/common/ViewToggle";
import { usePreferences } from "@/features/auth/hooks/queries/usePreferences";
import { MonthView, WeekView } from "@/features/calendar/components/CalendarViews";
import { useCalendarEvents } from "@/features/calendar/hooks/queries/useCalendarEvents";
import {
  calendarZone,
  eventsByDay,
  isSameMonth,
  parseCalendarParams,
  periodTitle,
  serializeCalendarParams,
  shiftParams,
  todayIn,
  visibleRange,
} from "@/features/calendar/lib/calendar";
import type { CalendarParams, CalendarView } from "@/features/calendar/types/Calendar";

const utc = (date: Date) => new Date(date.getTime()).toISOString();

export function CalendarPage() {
  const { t, i18n } = useTranslation();
  useDocumentTitle(t("calendar.title"));
  const preferences = usePreferences();
  // La zona de la cuenta (RF-130, decisión del usuario en F17): la misma que usan
  // los emails. Sin zona en la cuenta, la del navegador.
  const zone = calendarZone(preferences.data?.timezone);
  const today = todayIn(zone);

  // Vista y día de referencia en la URL, como los filtros de los listados.
  const [searchParams, setSearchParams] = useSearchParams();
  const params = parseCalendarParams(searchParams, today);
  const range = visibleRange(params, zone);
  const events = useCalendarEvents(utc(range.start), utc(range.end), {
    // Sin la zona de la cuenta, el rango sería el de otro día: se espera a tenerla.
    enabled: !preferences.isLoading,
  });

  const go = (next: CalendarParams) => setSearchParams(serializeCalendarParams(next, today));
  const byDay = eventsByDay(events.data?.events ?? [], zone);
  const visibleCount =
    params.view === "month"
      ? range.days.filter((day) => isSameMonth(day, params.date) && byDay.has(day)).length
      : byDay.size;
  const step = params.view === "month" ? "Month" : "Week";

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-center gap-4">
        <h1 className="text-2xl font-semibold">{t("calendar.title")}</h1>
        <ViewToggle<CalendarView>
          label={t("calendar.view")}
          options={[
            { value: "month", label: t("calendar.viewMonth"), icon: CalendarDays },
            { value: "week", label: t("calendar.viewWeek"), icon: CalendarRange },
          ]}
          value={params.view}
          onChange={(view) => go({ ...params, view })}
        />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => go({ ...params, date: today })}>
            {t("calendar.today")}
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label={t(`calendar.previous${step}`)}
            title={t(`calendar.previous${step}`)}
            onClick={() => go(shiftParams(params, -1, zone))}
          >
            <ChevronLeft />
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label={t(`calendar.next${step}`)}
            title={t(`calendar.next${step}`)}
            onClick={() => go(shiftParams(params, 1, zone))}
          >
            <ChevronRight />
          </Button>
          <h2 aria-live="polite" className="text-lg font-medium">
            {periodTitle(params, range.days, i18n.language)}
          </h2>
        </div>
        <p className="text-xs text-muted-foreground">{t("calendar.zone", { zone })}</p>
      </div>

      {(preferences.isLoading || events.isLoading) && <ListSkeleton rows={3} />}
      {events.isError && (
        <ErrorState onRetry={() => events.refetch()} retrying={events.isFetching} />
      )}
      {events.data && (
        <div
          className={cn("grid gap-3 transition-opacity", events.isPlaceholderData && "opacity-60")}
        >
          {visibleCount === 0 && (
            <p className="text-sm text-muted-foreground">
              {t(params.view === "month" ? "calendar.emptyMonth" : "calendar.emptyWeek")}
            </p>
          )}
          {params.view === "month" ? (
            <MonthView
              days={range.days}
              today={today}
              byDay={byDay}
              zone={zone}
              month={params.date}
              onShowDay={(day) => go({ view: "week", date: day })}
            />
          ) : (
            <WeekView days={range.days} today={today} byDay={byDay} zone={zone} />
          )}
        </div>
      )}
    </div>
  );
}
