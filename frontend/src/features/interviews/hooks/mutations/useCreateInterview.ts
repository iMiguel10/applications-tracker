import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAccountZone } from "@/features/auth/hooks/useAccountZone";
import { interviewService } from "../../services/interview.service";
import type { InterviewFormValues } from "../../schemas/interview.schema";
import { invalidateAfterInterviewChange } from "./invalidate";

export function useCreateInterview(applicationId: string) {
  const queryClient = useQueryClient();
  const zone = useAccountZone();

  return useMutation({
    mutationFn: (values: InterviewFormValues) =>
      interviewService.create(applicationId, values, zone),
    onSuccess: () => invalidateAfterInterviewChange(queryClient, applicationId),
  });
}
