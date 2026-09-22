import { useMutation, useQueryClient } from "@tanstack/react-query";
import { applicationService } from "../../services/application.service";
import type { ApplicationFormValues } from "../../schemas/application.schema";
import { invalidateAfterApplicationChange } from "./invalidate";

export function useUpdateApplication() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, values }: { id: string; values: ApplicationFormValues }) =>
      applicationService.update(id, values),
    onSuccess: () => invalidateAfterApplicationChange(queryClient),
  });
}
