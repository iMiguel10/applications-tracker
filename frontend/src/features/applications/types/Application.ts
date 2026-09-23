export const APPLICATION_STATUSES = [
  "saved",
  "applied",
  "screening",
  "interviewing",
  "offer",
  "accepted",
  "rejected",
  "withdrawn",
] as const;
export type ApplicationStatus = (typeof APPLICATION_STATUSES)[number];

/** Estados con los que se puede crear una solicitud (regla 5 de la especificación). */
export const INITIAL_STATUSES = ["saved", "applied"] as const;
export type InitialStatus = (typeof INITIAL_STATUSES)[number];

export const WORK_MODES = ["onsite", "hybrid", "remote"] as const;
export type WorkMode = (typeof WORK_MODES)[number];

export const APPLICATION_SOURCES = [
  "linkedin",
  "infojobs",
  "indeed",
  "company_website",
  "referral",
  "recruiter",
  "other",
] as const;
export type ApplicationSource = (typeof APPLICATION_SOURCES)[number];

export const CURRENCIES = ["EUR", "USD", "GBP", "CHF"] as const;
export type Currency = (typeof CURRENCIES)[number];

export interface CompanySummary {
  id: string;
  name: string;
}

export interface Application {
  id: string;
  company: CompanySummary;
  position_title: string;
  job_url: string | null;
  location: string | null;
  work_mode: WorkMode | null;
  source: ApplicationSource | null;
  origin: "manual";
  status: ApplicationStatus;
  /** Transiciones disponibles desde el estado actual (decisión A8): la única
   * fuente de verdad de qué ofrecer en el diálogo de cambio de estado. Vacío en
   * un estado final. */
  allowed_transitions: ApplicationStatus[];
  /** Fecha sin hora, "yyyy-MM-dd". */
  applied_at: string | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: Currency;
  notes: string | null;
  archived_at: string | null;
  last_activity_at: string;
  created_at: string;
  updated_at: string;
}

export type ArchivedFilter = "active" | "archived" | "all";
export type ApplicationSort =
  | "applied_at"
  | "created_at"
  | "updated_at"
  | "company"
  | "position_title";

export interface ApplicationListParams {
  page: number;
  limit: number;
  status: ApplicationStatus[];
  work_mode: WorkMode[];
  source: ApplicationSource[];
  company_id: string | null;
  applied_from: string | null;
  applied_to: string | null;
  q: string;
  archived: ArchivedFilter;
  sort_by: ApplicationSort;
  order: "asc" | "desc";
}
