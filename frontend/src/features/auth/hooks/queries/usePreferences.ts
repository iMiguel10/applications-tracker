import { useQuery } from "@tanstack/react-query";
import { authKeys } from "../../auth.keys";
import { preferencesService } from "../../services/preferences.service";

export function usePreferences() {
  return useQuery({
    queryKey: authKeys.preferences(),
    queryFn: preferencesService.get,
  });
}
