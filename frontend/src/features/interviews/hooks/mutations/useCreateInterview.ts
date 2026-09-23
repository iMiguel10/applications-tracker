import { useMutation, useQueryClient } from "@tanstack/react-query";
import { interviewService } from "../../services/interview.service";
import type { InterviewFormValues } from "../../schemas/interview.schema";
import { invalidateAfterInterviewChange } from "./invalidate";

export function useCreateInterview(applicationId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (values: InterviewFormValues) =>
      interviewService.create(applicationId, values),
    onSuccess: () => invalidateAfterInterviewChange(queryClient, applicationId),
  });
}
