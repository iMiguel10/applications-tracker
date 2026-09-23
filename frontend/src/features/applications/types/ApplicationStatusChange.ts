import type { ApplicationStatus } from "./Application";

export interface ApplicationStatusChange {
  id: string;
  /** `null` en el cambio inicial, que crea la solicitud. */
  from_status: ApplicationStatus | null;
  to_status: ApplicationStatus;
  changed_at: string;
  note: string | null;
  created_at: string;
}
