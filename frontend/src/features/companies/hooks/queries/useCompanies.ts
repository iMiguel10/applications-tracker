import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { companyKeys } from "../../company.keys";
import { companyService } from "../../services/company.service";
import type { CompanyListParams } from "../../types/Company";

export function useCompanies(params: CompanyListParams) {
  return useQuery({
    queryKey: companyKeys.list(params),
    queryFn: () => companyService.list(params),
    placeholderData: keepPreviousData,
  });
}
