import { useMutation, useQueryClient } from "@tanstack/react-query";
import { dashboardKeys } from "@/features/dashboard/dashboard.keys";
import { authKeys } from "../../auth.keys";
import { preferencesService } from "../../services/preferences.service";

export function useUpdatePreferences() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: preferencesService.update,
    onSuccess: (data) => {
      queryClient.setQueryData(authKeys.preferences(), data);
      // El umbral de "sin actividad" (RF-64) alimenta el dashboard.
      queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
    },
  });
}
