import { useMutation, useQueryClient } from "@tanstack/react-query";
import { reminderService } from "../../services/reminder.service";
import type { ReminderFormValues } from "../../schemas/reminder.schema";
import { invalidateAfterReminderChange } from "./invalidate";

export function useCreateReminder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (values: ReminderFormValues) => reminderService.create(values),
    onSuccess: () => invalidateAfterReminderChange(queryClient),
  });
}
