import { useMutation, useQueryClient } from "@tanstack/react-query";
import { profileKeys } from "../../profile.keys";
import { profileService } from "../../services/profile.service";

export function useDeleteEntry() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: profileService.deleteEntry,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: profileKeys.entries() }),
  });
}
