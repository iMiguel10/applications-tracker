import { useQuery } from "@tanstack/react-query";
import { usageKeys } from "../../usage.keys";
import { usageService } from "../../services/usage.service";

export function useUsage() {
  return useQuery({
    queryKey: usageKeys.all,
    queryFn: usageService.get,
    // Cambia con cada solicitud, empresa o recordatorio que se crea o se borra:
    // se vuelve a pedir cada vez que se monta (la tarjeta, un formulario).
    staleTime: 0,
  });
}
