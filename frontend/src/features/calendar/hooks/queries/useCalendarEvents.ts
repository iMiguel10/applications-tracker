import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { calendarKeys } from "../../calendar.keys";
import { calendarService } from "../../services/calendar.service";

/** Eventos de [start, end). Al cambiar de mes se queda el anterior a la vista
 * mientras llega el nuevo, en lugar de un esqueleto en cada clic. */
export function useCalendarEvents(start: string, end: string, { enabled = true } = {}) {
  return useQuery({
    queryKey: calendarKeys.events(start, end),
    queryFn: () => calendarService.events(start, end),
    placeholderData: keepPreviousData,
    enabled,
  });
}
