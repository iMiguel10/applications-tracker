import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAccountZone } from "@/features/auth/hooks/useAccountZone";
import { applicationStatusChangeService } from "../../services/applicationStatusChange.service";
import type { StatusChangeFormValues } from "../../schemas/statusChange.schema";
import { invalidateAfterApplicationChange } from "./invalidate";

export function useChangeStatus() {
  const queryClient = useQueryClient();
  const zone = useAccountZone();

  return useMutation({
    mutationFn: ({
      applicationId,
      values,
    }: {
      applicationId: string;
      values: StatusChangeFormValues;
    }) => applicationStatusChangeService.create(applicationId, values, zone),
    onSuccess: () => invalidateAfterApplicationChange(queryClient),
  });
}
