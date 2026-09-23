import { useMutation, useQueryClient } from "@tanstack/react-query";
import { interviewService } from "../../services/interview.service";
import { invalidateAfterInterviewChange } from "./invalidate";

export function useDeleteInterview(applicationId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (interviewId: string) => interviewService.remove(applicationId, interviewId),
    onSuccess: () => invalidateAfterInterviewChange(queryClient, applicationId),
  });
}
