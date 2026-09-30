import { useMutation, useQueryClient } from "@tanstack/react-query";
import { profileKeys } from "../../profile.keys";
import { profileService } from "../../services/profile.service";

export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: profileService.update,
    onSuccess: (data) => {
      queryClient.setQueryData(profileKeys.detail(), data);
    },
  });
}
