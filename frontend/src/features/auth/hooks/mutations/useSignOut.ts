import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { authService } from "../../services/auth.service";

export function useSignOut() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  return useMutation({
    mutationFn: authService.signOut,
    onSuccess: () => {
      // Primero vaciar la caché y después navegar: si se navega antes, la página de
      // login llega a montarse con datos del usuario que acaba de salir (T8).
      queryClient.clear();
      navigate("/login", { replace: true });
    },
  });
}
