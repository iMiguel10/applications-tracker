import { useMutation, useQueryClient } from "@tanstack/react-query";
import { applicationStatusChangeService } from "../../services/applicationStatusChange.service";
import { invalidateAfterApplicationChange } from "./invalidate";

export function useUndoLastStatusChange() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (applicationId: string) =>
      applicationStatusChangeService.undoLast(applicationId),
    onSuccess: () => invalidateAfterApplicationChange(queryClient),
  });
}
