import type { QueryClient } from "@tanstack/react-query";
import { dashboardKeys } from "@/features/dashboard/dashboard.keys";
import { reminderKeys } from "../../reminder.keys";

/** Crear, completar o descartar un recordatorio cambia también el widget de
 * recordatorios pendientes del dashboard (F5, RF-63). */
export function invalidateAfterReminderChange(queryClient: QueryClient) {
  queryClient.invalidateQueries({ queryKey: reminderKeys.all });
  queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
}
