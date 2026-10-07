import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAccountZone } from "@/features/auth/hooks/useAccountZone";
import { interviewService } from "../../services/interview.service";
import type { InterviewFormValues } from "../../schemas/interview.schema";
import { invalidateAfterInterviewChange } from "./invalidate";

export function useUpdateInterview(applicationId: string) {
  const queryClient = useQueryClient();
  const zone = useAccountZone();

  return useMutation({
    mutationFn: ({
      interviewId,
      values,
    }: {
      interviewId: string;
      values: InterviewFormValues;
    }) => interviewService.update(applicationId, interviewId, values, zone),
    onSuccess: () => invalidateAfterInterviewChange(queryClient, applicationId),
  });
}
