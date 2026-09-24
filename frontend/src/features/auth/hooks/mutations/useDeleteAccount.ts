import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { authService } from "../../services/auth.service";

export function useDeleteAccount() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  return useMutation({
    mutationFn: async () => {
      await authService.deleteAccount();
      // El access token sigue siendo válido hasta 5 min aunque la identidad ya no
      // exista: cerrar sesión borra las cookies. Si falla, la cuenta ya está borrada
      // y no hay nada que deshacer, así que no se trata como error.
      await authService.signOut().catch(() => undefined);
    },
    onSuccess: () => {
      // Igual que en useSignOut: vaciar la caché antes de navegar (T8).
      queryClient.clear();
      navigate("/login", { replace: true });
    },
    // Un fallo puede llegar después de borrar los datos propios (si falla SuperTokens,
    // decisión 0008): se vuelve a pedir todo para no seguir mostrando datos borrados.
    onError: () => queryClient.invalidateQueries(),
  });
}
