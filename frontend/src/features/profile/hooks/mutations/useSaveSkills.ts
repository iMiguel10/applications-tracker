import { useMutation, useQueryClient } from "@tanstack/react-query";
import { profileKeys } from "../../profile.keys";
import { profileSkillService } from "../../services/profile.service";

export function useSaveSkills() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: profileSkillService.saveSkills,
    onSuccess: (skills) => queryClient.setQueryData(profileKeys.skills(), skills),
  });
}

export function useSaveLanguages() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: profileSkillService.saveLanguages,
    onSuccess: (languages) => queryClient.setQueryData(profileKeys.languages(), languages),
  });
}
