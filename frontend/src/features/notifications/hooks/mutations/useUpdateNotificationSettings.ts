import { useMutation, useQueryClient } from "@tanstack/react-query";
import { authKeys } from "@/features/auth/auth.keys";
import type { Preferences } from "@/features/auth/types/Auth";
import { notificationSettingsService } from "../../services/notificationSettings.service";
import type { NotificationSettings } from "../../types/NotificationSettings";

/** Guarda al momento cada interruptor. Optimista: el interruptor cambia al pulsarlo
 * y vuelve atrás si la API falla. */
export function useUpdateNotificationSettings() {
  const queryClient = useQueryClient();
  const key = authKeys.preferences();

  return useMutation({
    mutationFn: (changes: Partial<NotificationSettings>) =>
      notificationSettingsService.update(changes),
    onMutate: async (changes) => {
      await queryClient.cancelQueries({ queryKey: key });
      const previous = queryClient.getQueryData<Preferences>(key);
      if (previous) queryClient.setQueryData<Preferences>(key, { ...previous, ...changes });
      return { previous };
    },
    onError: (_error, _changes, context) => {
      if (context?.previous) queryClient.setQueryData(key, context.previous);
    },
    onSuccess: (data) => queryClient.setQueryData(key, data),
  });
}
