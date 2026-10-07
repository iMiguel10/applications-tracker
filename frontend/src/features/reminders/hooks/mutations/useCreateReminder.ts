import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAccountZone } from "@/features/auth/hooks/useAccountZone";
import { reminderService } from "../../services/reminder.service";
import type { ReminderFormValues } from "../../schemas/reminder.schema";
import { invalidateAfterReminderChange } from "./invalidate";

export function useCreateReminder() {
  const queryClient = useQueryClient();
  const zone = useAccountZone();

  return useMutation({
    mutationFn: (values: ReminderFormValues) => reminderService.create(values, zone),
    onSuccess: () => invalidateAfterReminderChange(queryClient),
  });
}
