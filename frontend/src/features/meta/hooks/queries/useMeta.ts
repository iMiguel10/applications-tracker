import { useQuery } from "@tanstack/react-query";
import { metaKeys } from "../../meta.keys";
import { metaService } from "../../services/meta.service";

export function useMeta() {
  return useQuery({
    queryKey: metaKeys.all,
    queryFn: metaService.get,
    // Es configuración del servidor: no cambia mientras la página está abierta.
    staleTime: Infinity,
  });
}
