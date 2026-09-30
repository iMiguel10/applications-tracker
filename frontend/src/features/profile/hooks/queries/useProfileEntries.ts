import { useQuery } from "@tanstack/react-query";
import { profileKeys } from "../../profile.keys";
import { profileService } from "../../services/profile.service";

export function useProfileEntries() {
  return useQuery({
    queryKey: profileKeys.entries(),
    queryFn: profileService.listEntries,
  });
}
