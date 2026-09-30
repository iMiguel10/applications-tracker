import type { Preferences } from "@/features/auth/types/Auth";

/** Los avisos por email de F12 (RF-80…84), con su interruptor en las preferencias. */
export const NOTIFICATION_TOGGLES = [
  "notify_reminder_due",
  "notify_interview",
  "notify_weekly_digest",
  "notify_stale",
] as const;
export type NotificationToggle = (typeof NOTIFICATION_TOGGLES)[number];

/** Los avisos con antelación configurable y el campo que la guarda. */
export const NOTICE_FIELDS = {
  notify_reminder_due: "reminder_notice_hours",
  notify_interview: "interview_notice_hours",
} as const satisfies Partial<Record<NotificationToggle, keyof Preferences>>;
export type NoticeField = (typeof NOTICE_FIELDS)[keyof typeof NOTICE_FIELDS];

export type NotificationSettings = Pick<Preferences, NotificationToggle | NoticeField>;

/** Antelaciones que ofrece la interfaz. La API admite de 0 a 168 horas en el
 * recordatorio (0 = al vencer, RF-80) y de 1 a 168 en la entrevista (RF-81). */
export const NOTICE_HOURS: Record<NoticeField, readonly number[]> = {
  reminder_notice_hours: [0, 1, 24],
  interview_notice_hours: [1, 2, 6, 12, 24, 48, 72, 168],
};

/** Tipos de aviso de la API (`notification_deliveries.kind`) y el interruptor que
 * los desactiva: la página de baja nombra el aviso con la etiqueta del interruptor. */
export const TOGGLE_FOR_KIND = {
  reminder_due: "notify_reminder_due",
  interview_upcoming: "notify_interview",
  weekly_digest: "notify_weekly_digest",
  stale_application: "notify_stale",
} as const satisfies Record<string, NotificationToggle>;
export type NotificationKind = keyof typeof TOGGLE_FOR_KIND;

export interface UnsubscribeResult {
  kind: NotificationKind;
}
