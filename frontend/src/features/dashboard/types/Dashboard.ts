import type { ApplicationStatus } from "@/features/applications/types/Application";
import type { InterviewFormat, InterviewType } from "@/features/interviews/types/Interview";
import type { Reminder } from "@/features/reminders/types/Reminder";

export interface DashboardApplicationSummary {
  id: string;
  position_title: string;
  company: { id: string; name: string };
  status: ApplicationStatus;
}

export interface StatusCount {
  status: ApplicationStatus;
  count: number;
}

export interface WeeklyApplications {
  /** Lunes de esa semana ISO, "yyyy-MM-dd". */
  week_start: string;
  count: number;
}

export interface ResponseRate {
  sent_count: number;
  reached_count: number;
  /** `null` si `sent_count` es demasiado pequeño para ser representativo (RF-66). */
  rate: number | null;
}

export interface UpcomingInterview {
  id: string;
  scheduled_at: string;
  interview_type: InterviewType | null;
  format: InterviewFormat | null;
  application: DashboardApplicationSummary;
}

export interface StaleApplication {
  application: DashboardApplicationSummary;
  last_activity_at: string;
  days_since_activity: number;
}

export interface Dashboard {
  status_counts: StatusCount[];
  applications_per_week: WeeklyApplications[];
  response_rate: ResponseRate;

  upcoming_interviews: UpcomingInterview[];
  upcoming_interviews_total: number;
  pending_reminders: Reminder[];
  pending_reminders_total: number;
  stale_applications: StaleApplication[];
  stale_applications_total: number;
  stale_after_days: number;
}
