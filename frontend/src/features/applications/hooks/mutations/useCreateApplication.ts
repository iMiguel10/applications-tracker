import { useMutation, useQueryClient } from "@tanstack/react-query";
import { applicationKeys } from "../../application.keys";
import { applicationService } from "../../services/application.service";

export function useCreateApplication() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: applicationService.create,
    // Una solicitud nueva cambia todas las páginas del listado (orden y total).
    onSuccess: () => queryClient.invalidateQueries({ queryKey: applicationKeys.lists() }),
  });
}
