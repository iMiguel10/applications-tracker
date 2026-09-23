import type { QueryClient } from "@tanstack/react-query";
import { applicationKeys } from "@/features/applications/application.keys";
import { interviewKeys } from "../../interview.keys";

/** Tocar entrevistas cambia last_activity_at de la solicitud (arquitectura §5). */
export function invalidateAfterInterviewChange(
  queryClient: QueryClient,
  applicationId: string,
) {
  queryClient.invalidateQueries({ queryKey: interviewKeys.all(applicationId) });
  queryClient.invalidateQueries({ queryKey: applicationKeys.detail(applicationId) });
}
