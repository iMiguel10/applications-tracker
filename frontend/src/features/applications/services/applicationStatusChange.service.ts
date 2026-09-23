import { apiClient } from "@/shared/lib/apiClient";
import type { Application } from "../types/Application";
import type { ApplicationStatusChange } from "../types/ApplicationStatusChange";
import type { StatusChangeFormValues } from "../schemas/statusChange.schema";

/**
 * El formulario solo pide un día (RF-30), pero la API espera un instante con zona
 * horaria. Se combina con la hora local actual, no con medianoche: así, si el
 * usuario elige el día de hoy sin pensarlo, el resultado sigue siendo "ahora
 * mismo" y no cae antes del último cambio (422 changed_at_before_last_change).
 */
export function toChangedAt(dateOnly: string): string {
  const [year, month, day] = dateOnly.split("-").map(Number);
  const now = new Date();
  return new Date(
    year,
    month - 1,
    day,
    now.getHours(),
    now.getMinutes(),
    now.getSeconds(),
  ).toISOString();
}

export const applicationStatusChangeService = {
  list: (applicationId: string) =>
    apiClient.get<ApplicationStatusChange[]>(
      `/applications/${applicationId}/status-changes`,
    ),

  create: (applicationId: string, values: StatusChangeFormValues) =>
    apiClient.post<Application>(`/applications/${applicationId}/status-changes`, {
      to_status: values.to_status,
      changed_at: values.changed_at ? toChangedAt(values.changed_at) : null,
      note: values.note || null,
    }),

  undoLast: (applicationId: string) =>
    apiClient.delete<Application>(`/applications/${applicationId}/status-changes/last`),
};
