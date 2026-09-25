import { useMutation, useQueryClient } from "@tanstack/react-query";
import { authKeys } from "../../auth.keys";
import { authService } from "../../services/auth.service";

export function useVerifyEmail() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: authService.verifyEmail,
    onSuccess: (result) => {
      // Si hay sesión en este navegador, volver a preguntar también actualiza el
      // dato dentro de su access token (autenticación §8).
      if (result === "ok") {
        void queryClient.invalidateQueries({ queryKey: authKeys.emailVerified() });
      }
    },
  });
}
