import { useMutation, useQueryClient } from "@tanstack/react-query";
import { authService } from "../../services/auth.service";

export function useSubmitNewPassword() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (password: string) => {
      const result = await authService.submitNewPassword(password);
      if (result.status === "ok" && (await authService.sessionExists())) {
        // El backend ya ha revocado todas las sesiones, también la de este
        // navegador, pero su access token seguiría valiendo hasta 5 minutos
        // (decisión 0002). Se cierra aquí para no aparentar que se sigue dentro.
        await authService.signOut().catch(() => undefined);
      }
      return result;
    },
    onSuccess: (result) => {
      if (result.status === "ok") queryClient.clear();
    },
  });
}
