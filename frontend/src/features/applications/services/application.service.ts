import { apiClient } from "@/shared/lib/apiClient";
import type { Page } from "@/shared/types/Page";
import type { Application, ApplicationListParams } from "../types/Application";
import type { CreateApplicationFormValues } from "../schemas/application.schema";

export const applicationService = {
  list: ({ page, limit }: ApplicationListParams) =>
    apiClient.get<Page<Application>>(`/applications?page=${page}&limit=${limit}`),

  create: (data: CreateApplicationFormValues) =>
    apiClient.post<Application>("/applications", data),
};
