import { useMutation, useQueryClient } from "@tanstack/react-query";
import { interviewService } from "../../services/interview.service";
import type { InterviewFormValues } from "../../schemas/interview.schema";
import { invalidateAfterInterviewChange } from "./invalidate";

export function useUpdateInterview(applicationId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      interviewId,
      values,
    }: {
      interviewId: string;
      values: InterviewFormValues;
    }) => interviewService.update(applicationId, interviewId, values),
    onSuccess: () => invalidateAfterInterviewChange(queryClient, applicationId),
  });
}
