import { useQuery } from "@tanstack/react-query";
import { authKeys } from "../../auth.keys";
import { authService } from "../../services/auth.service";

export function useMe() {
  return useQuery({
    queryKey: authKeys.me(),
    queryFn: authService.getMe,
    // El usuario no cambia durante la sesión; al cerrarla se vacía toda la caché.
    staleTime: Infinity,
  });
}
