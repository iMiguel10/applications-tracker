import { useMutation, useQueryClient } from "@tanstack/react-query";
import { authKeys } from "@/features/auth/auth.keys";
import { unsubscribeService } from "../../services/unsubscribe.service";

export function useUnsubscribe() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (token: string) => unsubscribeService.confirm(token),
    // Si hay sesión en este navegador, la tarjeta de avisos debe mostrar el cambio.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: authKeys.preferences() }),
  });
}
