import { apiClient } from "@/shared/lib/apiClient";
import { datetimeLocalToIso } from "@/shared/lib/dates";
import { toQueryString } from "@/shared/lib/queryString";
import type { Page } from "@/shared/types/Page";
import type { Reminder, ReminderListParams } from "../types/Reminder";
import type { ReminderFormValues } from "../schemas/reminder.schema";

export const reminderService = {
  list: (params: ReminderListParams) =>
    apiClient.get<Page<Reminder>>(`/reminders${toQueryString({ ...params })}`),

  create: (values: ReminderFormValues) =>
    apiClient.post<Reminder>("/reminders", {
      title: values.title,
      due_at: datetimeLocalToIso(values.due_at),
      application_id: values.application_id || null,
    }),

  complete: (id: string) => apiClient.post<Reminder>(`/reminders/${id}/complete`),

  dismiss: (id: string) => apiClient.post<Reminder>(`/reminders/${id}/dismiss`),
};
