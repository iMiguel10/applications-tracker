export const calendarKeys = {
  all: ["calendar"] as const,
  events: (start: string, end: string) => [...calendarKeys.all, "events", start, end] as const,
};
