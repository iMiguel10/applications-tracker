import { useQuery } from "@tanstack/react-query";
import { documentKeys } from "../../document.keys";
import { documentService } from "../../services/document.service";

/** Los diseños de CV (RF-104). Cambian solo al desplegar: no se vuelven a pedir. */
export function useCvDesigns() {
  return useQuery({
    queryKey: documentKeys.cvDesigns(),
    queryFn: documentService.cvDesigns,
    staleTime: Infinity,
  });
}
