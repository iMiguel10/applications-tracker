import { apiClient } from "@/shared/lib/apiClient";
import { toQueryString } from "@/shared/lib/queryString";
import type { Page } from "@/shared/types/Page";
import type { Application, ApplicationListParams } from "../types/Application";
import type { ApplicationFormValues } from "../schemas/application.schema";

/** Formulario → cuerpo de la API: "" en un número es null, no 0. */
function toPayload(values: ApplicationFormValues) {
  const number = (value: string) => (value === "" ? null : Number(value));
  return {
    company_id: values.company_id,
    position_title: values.position_title,
    job_url: values.job_url,
    location: values.location,
    work_mode: values.work_mode,
    source: values.source,
    applied_at: values.applied_at,
    salary_min: number(values.salary_min),
    salary_max: number(values.salary_max),
    salary_currency: values.salary_currency,
    notes: values.notes,
  };
}

export const applicationService = {
  list: (params: ApplicationListParams) =>
    apiClient.get<Page<Application>>(
      `/applications${toQueryString({
        ...params,
        q: params.q || null,
      })}`,
    ),

  get: (id: string) => apiClient.get<Application>(`/applications/${id}`),

  create: (values: ApplicationFormValues) =>
    apiClient.post<Application>("/applications", { ...toPayload(values), status: values.status }),

  // Se envía el formulario completo: PATCH solo cambia lo enviado, y aquí se envía
  // todo lo editable (el estado no, que tiene su propia operación en F3).
  update: (id: string, values: ApplicationFormValues) =>
    apiClient.patch<Application>(`/applications/${id}`, toPayload(values)),

  archive: (id: string) => apiClient.post<Application>(`/applications/${id}/archive`),

  unarchive: (id: string) => apiClient.post<Application>(`/applications/${id}/unarchive`),

  remove: (id: string) => apiClient.delete<void>(`/applications/${id}`),
};
