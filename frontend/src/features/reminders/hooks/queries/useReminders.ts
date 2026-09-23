import { useQuery } from "@tanstack/react-query";
import { reminderKeys } from "../../reminder.keys";
import { reminderService } from "../../services/reminder.service";
import type { ReminderListParams } from "../../types/Reminder";

export function useReminders(params: ReminderListParams) {
  return useQuery({
    queryKey: reminderKeys.list(params),
    queryFn: () => reminderService.list(params),
  });
}
