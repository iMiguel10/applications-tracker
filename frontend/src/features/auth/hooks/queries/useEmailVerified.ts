import { useQuery } from "@tanstack/react-query";
import { authKeys } from "../../auth.keys";
import { authService } from "../../services/auth.service";

/** Si el email de la sesión está verificado. Se vuelve a preguntar al recuperar el
 * foco: así el aviso desaparece al volver de verificar en otra pestaña u otro
 * dispositivo. */
export function useEmailVerified({ enabled = true }: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: authKeys.emailVerified(),
    queryFn: authService.isEmailVerified,
    enabled,
    // Explícito: el queryClient desactiva por defecto el refresco al recuperar el
    // foco y guarda las respuestas 5 minutos, y aquí hace falta lo contrario.
    staleTime: 0,
    refetchOnWindowFocus: true,
  });
}
