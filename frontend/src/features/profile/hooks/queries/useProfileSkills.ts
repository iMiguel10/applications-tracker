import { useQuery } from "@tanstack/react-query";
import { profileKeys } from "../../profile.keys";
import { profileSkillService } from "../../services/profile.service";

export function useProfileSkills() {
  return useQuery({ queryKey: profileKeys.skills(), queryFn: profileSkillService.listSkills });
}

export function useProfileLanguages() {
  return useQuery({
    queryKey: profileKeys.languages(),
    queryFn: profileSkillService.listLanguages,
  });
}
