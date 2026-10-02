export type CalendarEventKind = "interview" | "reminder";
export type CalendarView = "month" | "week";

export interface CalendarApplication {
  id: string;
  position_title: string;
  company: { id: string; name: string };
}

/** Una entrevista o un recordatorio pendiente (RF-130). Los campos de entrevista
 * son null en un recordatorio, y `title` es null en una entrevista. */
export interface CalendarEvent {
  kind: CalendarEventKind;
  id: string;
  starts_at: string;
  duration_minutes: number | null;
  title: string | null;
  interview_type: string | null;
  format: string | null;
  interviewers: string | null;
  outcome: string | null;
  application: CalendarApplication | null;
}

export interface CalendarEvents {
  events: CalendarEvent[];
}

/** Lo que pinta la página: la vista y un día de referencia ("yyyy-MM-dd") en la
 * zona de la cuenta. Va en la URL. */
export interface CalendarParams {
  view: CalendarView;
  date: string;
}
