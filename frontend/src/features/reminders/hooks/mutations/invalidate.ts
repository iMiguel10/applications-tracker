import type { QueryClient } from "@tanstack/react-query";
import { dashboardKeys } from "@/features/dashboard/dashboard.keys";
import { usageKeys } from "@/features/usage/usage.keys";
import { reminderKeys } from "../../reminder.keys";

/** Crear, completar, descartar o borrar un recordatorio cambia también el widget
 * de recordatorios pendientes del dashboard (F5, RF-63) y el uso de la cuenta. */
export function invalidateAfterReminderChange(queryClient: QueryClient) {
  queryClient.invalidateQueries({ queryKey: reminderKeys.all });
  queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
  queryClient.invalidateQueries({ queryKey: usageKeys.all });
}
