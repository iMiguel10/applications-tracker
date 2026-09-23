import { useMutation, useQueryClient } from "@tanstack/react-query";
import { reminderService } from "../../services/reminder.service";
import { invalidateAfterReminderChange } from "./invalidate";

export function useDismissReminder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: reminderService.dismiss,
    onSuccess: () => invalidateAfterReminderChange(queryClient),
  });
}
