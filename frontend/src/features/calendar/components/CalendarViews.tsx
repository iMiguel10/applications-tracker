import { useTranslation } from "react-i18next";

import { cn } from "@/shared/lib/utils";
import { entryFromEvent } from "../lib/addToCalendar";
import { formatDay, isSameMonth } from "../lib/calendar";
import type { CalendarEvent } from "../types/Calendar";
import { AddToCalendarMenu } from "./AddToCalendarMenu";
import { CalendarEventItem } from "./CalendarEventItem";

/** Cuántos eventos caben en la celda de un día del mes; el resto, "N más". */
const MONTH_CELL_EVENTS = 3;

interface ViewProps {
  days: string[];
  today: string;
  byDay: Map<string, CalendarEvent[]>;
  zone: string;
}

function DayNumber({ day, today, muted }: { day: string; today: string; muted?: boolean }) {
  return (
    <span
      aria-hidden
      className={cn(
        "inline-flex size-6 items-center justify-center rounded-full text-xs tabular-nums",
        day === today
          ? "bg-primary font-semibold text-primary-foreground"
          : muted
            ? "text-muted-foreground"
            : "font-medium",
      )}
    >
      {Number(day.slice(8))}
    </span>
  );
}

function useDayLabel() {
  const { t, i18n } = useTranslation();
  return (day: string, count: number) =>
    t("calendar.dayLabel", {
      day: formatDay(day, i18n.language, { weekday: "long", day: "numeric", month: "long" }),
      count,
    });
}

/**
 * El mes en rejilla de lunes a domingo (RF-130). En pantallas estrechas siete
 * columnas no caben: se ve como una agenda con solo los días que tienen algo.
 */
export function MonthView({
  days,
  today,
  byDay,
  zone,
  month,
  onShowDay,
}: ViewProps & { month: string; onShowDay: (day: string) => void }) {
  const { t, i18n } = useTranslation();
  const dayLabel = useDayLabel();
  const busyDays = days.filter((day) => isSameMonth(day, month) && byDay.has(day));

  return (
    <>
      <div className="hidden md:block">
        <div aria-hidden className="grid grid-cols-7 pb-1 text-xs text-muted-foreground">
          {days.slice(0, 7).map((day) => (
            <span key={day} className="px-2">
              {formatDay(day, i18n.language, { weekday: "short" })}
            </span>
          ))}
        </div>
        <ol className="grid grid-cols-7 overflow-hidden rounded-xl border bg-border gap-px">
          {days.map((day) => {
            const events = byDay.get(day) ?? [];
            const hidden = events.length - MONTH_CELL_EVENTS;
            const outside = !isSameMonth(day, month);
            return (
              <li
                key={day}
                className={cn(
                  "flex min-h-28 min-w-0 flex-col gap-1 p-1.5",
                  outside ? "bg-muted/40" : "bg-card",
                )}
              >
                <DayNumber day={day} today={today} muted={outside} />
                <span className="sr-only">{dayLabel(day, events.length)}</span>
                {/* grid-cols-1 (minmax(0, 1fr)): sin ella, la columna crece hasta el
                    ancho del texto entero y el evento se sale de la celda. */}
                <ul className="grid grid-cols-1 gap-0.5">
                  {events.slice(0, MONTH_CELL_EVENTS).map((event) => (
                    <li key={`${event.kind}-${event.id}`}>
                      <CalendarEventItem event={event} zone={zone} compact />
                    </li>
                  ))}
                </ul>
                {hidden > 0 && (
                  <button
                    type="button"
                    onClick={() => onShowDay(day)}
                    className="self-start rounded px-1.5 text-xs text-muted-foreground underline-offset-2 hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none"
                  >
                    {t("calendar.more", { count: hidden })}
                  </button>
                )}
              </li>
            );
          })}
        </ol>
      </div>

      <ol className="grid grid-cols-1 gap-4 md:hidden">
        {busyDays.map((day) => (
          <DaySection key={day} day={day} today={today} events={byDay.get(day) ?? []} zone={zone} />
        ))}
      </ol>
    </>
  );
}

/** La semana: un día por columna, o uno debajo de otro en pantallas estrechas. */
export function WeekView({ days, today, byDay, zone }: ViewProps) {
  return (
    <ol className="grid grid-cols-1 gap-4 md:grid-cols-7 md:gap-2">
      {days.map((day) => (
        <DaySection key={day} day={day} today={today} events={byDay.get(day) ?? []} zone={zone} />
      ))}
    </ol>
  );
}

function DaySection({
  day,
  today,
  events,
  zone,
}: {
  day: string;
  today: string;
  events: CalendarEvent[];
  zone: string;
}) {
  const { t, i18n } = useTranslation();
  const dayLabel = useDayLabel();
  return (
    <li className="grid min-w-0 grid-cols-1 content-start gap-2">
      <div className="flex items-center gap-2 border-b pb-1">
        <DayNumber day={day} today={today} />
        <span className="sr-only">{dayLabel(day, events.length)}</span>
        <span aria-hidden className="text-sm text-muted-foreground">
          {formatDay(day, i18n.language, { weekday: "long" })}
        </span>
      </div>
      {events.length > 0 ? (
        <ul className="grid grid-cols-1 gap-1.5">
          {events.map((event) => (
            // El menú va dentro de la tarjeta, en su esquina: al lado le quitaría ancho
            // al evento en las columnas estrechas de la semana.
            <li key={`${event.kind}-${event.id}`} className="relative">
              <CalendarEventItem event={event} zone={zone} className="pr-8" />
              <AddToCalendarMenu
                entry={entryFromEvent(event, t, window.location.origin)}
                className="absolute top-1 right-1 size-6"
              />
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-muted-foreground">{t("calendar.noEvents")}</p>
      )}
    </li>
  );
}
