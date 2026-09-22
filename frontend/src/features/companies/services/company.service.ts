import { apiClient } from "@/shared/lib/apiClient";
import { toQueryString } from "@/shared/lib/queryString";
import type { Page } from "@/shared/types/Page";
import type { Company, CompanyListParams } from "../types/Company";
import type { CompanyFormValues } from "../schemas/company.schema";

// Los campos opcionales vacíos viajan como "": el backend los guarda como null.
export const companyService = {
  list: (params: CompanyListParams) =>
    apiClient.get<Page<Company>>(`/companies${toQueryString({ ...params })}`),

  get: (id: string) => apiClient.get<Company>(`/companies/${id}`),

  create: (data: CompanyFormValues) => apiClient.post<Company>("/companies", data),

  update: (id: string, data: CompanyFormValues) =>
    apiClient.patch<Company>(`/companies/${id}`, data),

  remove: (id: string) => apiClient.delete<void>(`/companies/${id}`),
};
