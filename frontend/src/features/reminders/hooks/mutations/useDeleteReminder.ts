import { useMutation, useQueryClient } from "@tanstack/react-query";
import { reminderService } from "../../services/reminder.service";
import { invalidateAfterReminderChange } from "./invalidate";

export function useDeleteReminder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: reminderService.remove,
    onSuccess: () => invalidateAfterReminderChange(queryClient),
  });
}
