import type { QueryClient } from "@tanstack/react-query";
import { calendarKeys } from "@/features/calendar/calendar.keys";
import { dashboardKeys } from "@/features/dashboard/dashboard.keys";
import { usageKeys } from "@/features/usage/usage.keys";
import { reminderKeys } from "../../reminder.keys";

/** Crear, completar, descartar o borrar un recordatorio cambia también el widget
 * de recordatorios pendientes del dashboard (F5, RF-63), el uso de la cuenta y el
 * calendario (F17). */
export function invalidateAfterReminderChange(queryClient: QueryClient) {
  queryClient.invalidateQueries({ queryKey: reminderKeys.all });
  queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
  queryClient.invalidateQueries({ queryKey: usageKeys.all });
  queryClient.invalidateQueries({ queryKey: calendarKeys.all });
}
