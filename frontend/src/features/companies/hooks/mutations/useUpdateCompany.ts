import { useMutation, useQueryClient } from "@tanstack/react-query";
import { applicationKeys } from "@/features/applications/application.keys";
import { calendarKeys } from "@/features/calendar/calendar.keys";
import { companyKeys } from "../../company.keys";
import { companyService } from "../../services/company.service";
import type { CompanyFormValues } from "../../schemas/company.schema";

export function useUpdateCompany() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: CompanyFormValues }) =>
      companyService.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: companyKeys.all });
      // El nombre de la empresa aparece en las solicitudes y en el calendario.
      queryClient.invalidateQueries({ queryKey: applicationKeys.all });
      queryClient.invalidateQueries({ queryKey: calendarKeys.all });
    },
  });
}
