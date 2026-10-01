import type { QueryClient } from "@tanstack/react-query";
import { calendarKeys } from "@/features/calendar/calendar.keys";
import { applicationKeys } from "@/features/applications/application.keys";
import { dashboardKeys } from "@/features/dashboard/dashboard.keys";
import { interviewKeys } from "../../interview.keys";

/** Tocar entrevistas cambia last_activity_at de la solicitud (arquitectura §5),
 * las próximas entrevistas del dashboard (F5, RF-63) y el calendario (F17). */
export function invalidateAfterInterviewChange(
  queryClient: QueryClient,
  applicationId: string,
) {
  queryClient.invalidateQueries({ queryKey: interviewKeys.all(applicationId) });
  queryClient.invalidateQueries({ queryKey: applicationKeys.detail(applicationId) });
  queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
  queryClient.invalidateQueries({ queryKey: calendarKeys.all });
}
