import { useMutation, useQueryClient } from "@tanstack/react-query";
import { companyKeys } from "../../company.keys";
import { companyService } from "../../services/company.service";

export function useCreateCompany() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: companyService.create,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: companyKeys.lists() }),
  });
}
