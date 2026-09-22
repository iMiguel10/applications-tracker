import { useMutation, useQueryClient } from "@tanstack/react-query";
import { applicationService } from "../../services/application.service";
import { invalidateAfterApplicationChange } from "./invalidate";

export function useSetArchived() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, archived }: { id: string; archived: boolean }) =>
      archived ? applicationService.archive(id) : applicationService.unarchive(id),
    onSuccess: () => invalidateAfterApplicationChange(queryClient),
  });
}
