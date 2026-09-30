import type { Preferences } from "@/features/auth/types/Auth";

/** Los avisos por email de F12 (RF-80…84), con su interruptor en las preferencias. */
export const NOTIFICATION_TOGGLES = [
  "notify_reminder_due",
  "notify_interview",
  "notify_weekly_digest",
  "notify_stale",
] as const;
export type NotificationToggle = (typeof NOTIFICATION_TOGGLES)[number];

export type NotificationSettings = Pick<
  Preferences,
  NotificationToggle | "interview_notice_hours"
>;

/** Antelaciones que ofrece la interfaz (RF-81). La API admite de 1 a 168 horas. */
export const INTERVIEW_NOTICE_HOURS = [1, 2, 6, 12, 24, 48, 72, 168] as const;
