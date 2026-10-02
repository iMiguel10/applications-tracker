import { Bell, Users } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { cn } from "@/shared/lib/utils";
import { eventHref, formatTime, isOverdue } from "../lib/calendar";
import type { CalendarEvent } from "../types/Calendar";

interface CalendarEventItemProps {
  event: CalendarEvent;
  zone: string;
  /** En la celda de un mes: una sola línea, recortada. */
  compact?: boolean;
  className?: string;
}

/** Un evento del calendario, enlazado a su solicitud o a los recordatorios (RF-131). */
export function CalendarEventItem({
  event,
  zone,
  compact = false,
  className,
}: CalendarEventItemProps) {
  const { t, i18n } = useTranslation();
  const time = formatTime(event.starts_at, zone, i18n.language);
  const overdue = isOverdue(event);
  const interview = event.kind === "interview";
  const Icon = interview ? Users : Bell;
  const application = event.application;

  const title = interview
    ? t("calendar.interviewOf", { position: application?.position_title })
    : (event.title ?? "");
  const details = [
    interview && event.interview_type ? t(`interviews.type.${event.interview_type}`) : null,
    application ? (interview ? application.company.name : `${application.position_title} · ${application.company.name}`) : null,
    interview && event.outcome && event.outcome !== "pending"
      ? t(`interviews.outcome.${event.outcome}`)
      : null,
  ].filter(Boolean);
  // Lo que oye un lector de pantalla: todo, también lo que la celda recorta.
  const label = [
    time,
    title,
    ...details,
    overdue ? t("calendar.overdue") : null,
  ]
    .filter(Boolean)
    .join(", ");

  return (
    <Link
      to={eventHref(event)}
      aria-label={label}
      title={compact ? label : undefined}
      className={cn(
        "flex min-w-0 gap-1.5 rounded-md text-left transition-colors focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none",
        compact ? "items-center px-1.5 py-0.5 text-xs" : "items-start p-2 text-sm",
        interview
          ? "bg-primary/10 text-foreground hover:bg-primary/15"
          : overdue
            ? "bg-destructive/10 text-foreground hover:bg-destructive/15"
            : "border bg-card text-foreground hover:bg-muted",
        className,
      )}
    >
      <Icon
        aria-hidden
        className={cn(
          "shrink-0",
          compact ? "size-3" : "mt-0.5 size-3.5",
          interview ? "text-primary" : overdue ? "text-destructive" : "text-muted-foreground",
        )}
      />
      {compact ? (
        <span className="truncate">
          <span className="tabular-nums text-muted-foreground">{time}</span> {title}
        </span>
      ) : (
        <span className="grid min-w-0 gap-0.5">
          <span className="font-medium [overflow-wrap:anywhere]">
            <span className="tabular-nums text-muted-foreground">{time}</span> {title}
          </span>
          {details.length > 0 && (
            <span className="truncate text-xs text-muted-foreground">{details.join(" · ")}</span>
          )}
          {overdue && (
            <span className="text-xs font-medium text-destructive">{t("calendar.overdue")}</span>
          )}
        </span>
      )}
    </Link>
  );
}
