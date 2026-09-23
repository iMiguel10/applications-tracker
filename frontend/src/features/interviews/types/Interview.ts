export const INTERVIEW_TYPES = [
  "screening",
  "technical",
  "hr",
  "cultural",
  "final",
  "other",
] as const;
export type InterviewType = (typeof INTERVIEW_TYPES)[number];

export const INTERVIEW_FORMATS = ["online", "onsite", "phone"] as const;
export type InterviewFormat = (typeof INTERVIEW_FORMATS)[number];

export const INTERVIEW_OUTCOMES = ["pending", "passed", "failed", "cancelled"] as const;
export type InterviewOutcome = (typeof INTERVIEW_OUTCOMES)[number];

export interface Interview {
  id: string;
  /** Instante ISO con zona. */
  scheduled_at: string;
  duration_minutes: number | null;
  interviewers: string | null;
  interview_type: InterviewType | null;
  format: InterviewFormat | null;
  outcome: InterviewOutcome;
  notes: string | null;
  created_at: string;
  updated_at: string;
}
