import { useMutation, useQueryClient } from "@tanstack/react-query";
import { authService } from "../../services/auth.service";

export function useSignIn() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: authService.signIn,
    // Nada de la caché puede venir de otra sesión anterior en este navegador.
    onSuccess: (result) => {
      if (result.status === "ok") queryClient.clear();
    },
  });
}
