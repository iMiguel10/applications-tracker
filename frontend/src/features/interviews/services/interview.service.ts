import { apiClient } from "@/shared/lib/apiClient";
import { datetimeLocalToIso } from "@/shared/lib/dates";
import type { Interview } from "../types/Interview";
import type { InterviewFormValues } from "../schemas/interview.schema";

function toPayload(values: InterviewFormValues) {
  return {
    scheduled_at: datetimeLocalToIso(values.scheduled_at),
    duration_minutes: values.duration_minutes === "" ? null : Number(values.duration_minutes),
    interviewers: values.interviewers || null,
    interview_type: values.interview_type,
    format: values.format,
    // Ignorado por InterviewCreate (no tiene ese campo); usado por InterviewUpdate.
    outcome: values.outcome,
    notes: values.notes || null,
  };
}

export const interviewService = {
  list: (applicationId: string) =>
    apiClient.get<Interview[]>(`/applications/${applicationId}/interviews`),

  create: (applicationId: string, values: InterviewFormValues) =>
    apiClient.post<Interview>(`/applications/${applicationId}/interviews`, toPayload(values)),

  update: (applicationId: string, interviewId: string, values: InterviewFormValues) =>
    apiClient.patch<Interview>(
      `/applications/${applicationId}/interviews/${interviewId}`,
      toPayload(values),
    ),

  remove: (applicationId: string, interviewId: string) =>
    apiClient.delete<void>(`/applications/${applicationId}/interviews/${interviewId}`),
};
