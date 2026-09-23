import type { ReminderListParams } from "./types/Reminder";

export const reminderKeys = {
  all: ["reminders"] as const,
  lists: () => [...reminderKeys.all, "list"] as const,
  list: (params: ReminderListParams) => [...reminderKeys.lists(), params] as const,
};
