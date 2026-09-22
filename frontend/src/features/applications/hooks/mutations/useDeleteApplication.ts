import { useMutation, useQueryClient } from "@tanstack/react-query";
import { applicationService } from "../../services/application.service";
import { invalidateAfterApplicationChange } from "./invalidate";

export function useDeleteApplication() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: applicationService.remove,
    onSuccess: () => invalidateAfterApplicationChange(queryClient),
  });
}
