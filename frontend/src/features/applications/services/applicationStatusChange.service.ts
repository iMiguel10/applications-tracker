import { TZDate } from "@date-fns/tz";

import { apiClient } from "@/shared/lib/apiClient";
import type { Application } from "../types/Application";
import type { ApplicationStatusChange } from "../types/ApplicationStatusChange";
import type { StatusChangeFormValues } from "../schemas/statusChange.schema";

/**
 * El formulario solo pide un día (RF-30), pero la API espera un instante con zona
 * horaria. Se combina con la hora actual en la zona de la cuenta, no con
 * medianoche: así, si el usuario elige el día de hoy sin pensarlo, el resultado
 * sigue siendo "ahora mismo" y no cae antes del último cambio (422
 * changed_at_before_last_change). Es el mismo criterio que `initial_change_at` del
 * backend (0015).
 */
export function toChangedAt(dateOnly: string, zone: string, now: Date = new Date()): string {
  const [year, month, day] = dateOnly.split("-").map(Number);
  const clock = new TZDate(now, zone);
  const changedAt = new TZDate(
    year,
    month - 1,
    day,
    clock.getHours(),
    clock.getMinutes(),
    clock.getSeconds(),
    zone,
  );
  // TZDate escribe toISOString con el desfase de su zona: se pasa por un Date.
  return new Date(changedAt.getTime()).toISOString();
}

export const applicationStatusChangeService = {
  list: (applicationId: string) =>
    apiClient.get<ApplicationStatusChange[]>(
      `/applications/${applicationId}/status-changes`,
    ),

  /** `zone`: la de la cuenta, en la que se elige el día (`useAccountZone`). */
  create: (applicationId: string, values: StatusChangeFormValues, zone: string) =>
    apiClient.post<Application>(`/applications/${applicationId}/status-changes`, {
      to_status: values.to_status,
      changed_at: values.changed_at ? toChangedAt(values.changed_at, zone) : null,
      note: values.note || null,
    }),

  undoLast: (applicationId: string) =>
    apiClient.delete<Application>(`/applications/${applicationId}/status-changes/last`),
};
