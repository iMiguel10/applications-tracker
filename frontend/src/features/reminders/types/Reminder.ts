export const REMINDER_STATUSES = ["pending", "done", "dismissed"] as const;
export type ReminderStatus = (typeof REMINDER_STATUSES)[number];

export interface ReminderApplicationSummary {
  id: string;
  position_title: string;
}

export interface Reminder {
  id: string;
  title: string;
  /** Instante ISO con zona. */
  due_at: string;
  application: ReminderApplicationSummary | null;
  /** `null` en el MVP: el único canal (in_app) no envía nada (RF-53). */
  sent_at: string | null;
  completed_at: string | null;
  channel: "in_app";
  status: ReminderStatus;
  created_at: string;
  updated_at: string;
}

export type ReminderStatusFilter = "pending" | "done" | "dismissed" | "all";

export interface ReminderListParams {
  page: number;
  limit: number;
  application_id?: string;
  status: ReminderStatusFilter;
  sort_by: "due_at" | "created_at";
  order: "asc" | "desc";
}
