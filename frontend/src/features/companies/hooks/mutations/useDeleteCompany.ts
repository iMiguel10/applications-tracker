import { useMutation, useQueryClient } from "@tanstack/react-query";
import { companyKeys } from "../../company.keys";
import { companyService } from "../../services/company.service";

export function useDeleteCompany() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: companyService.remove,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: companyKeys.all }),
  });
}
