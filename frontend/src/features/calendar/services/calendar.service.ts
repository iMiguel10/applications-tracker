import { apiClient } from "@/shared/lib/apiClient";
import { toQueryString } from "@/shared/lib/queryString";
import type { CalendarEvents } from "../types/Calendar";

export const calendarService = {
  /** `start` y `end`, instantes ISO en UTC: [start, end), como mucho 62 días. */
  events: (start: string, end: string) =>
    apiClient.get<CalendarEvents>(`/calendar/events${toQueryString({ start, end })}`),
};
