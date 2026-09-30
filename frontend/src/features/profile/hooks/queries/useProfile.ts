import { useQuery } from "@tanstack/react-query";
import { profileKeys } from "../../profile.keys";
import { profileService } from "../../services/profile.service";

export function useProfile() {
  return useQuery({
    queryKey: profileKeys.detail(),
    queryFn: profileService.get,
  });
}
