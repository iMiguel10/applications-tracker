import { useMutation, useQueryClient } from "@tanstack/react-query";
import { applicationService } from "../../services/application.service";
import { invalidateAfterApplicationChange } from "./invalidate";

export function useCreateApplication() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: applicationService.create,
    onSuccess: () => invalidateAfterApplicationChange(queryClient),
  });
}
