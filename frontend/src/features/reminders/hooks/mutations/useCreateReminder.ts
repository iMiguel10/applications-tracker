import { useMutation, useQueryClient } from "@tanstack/react-query";
import { reminderKeys } from "../../reminder.keys";
import { reminderService } from "../../services/reminder.service";
import type { ReminderFormValues } from "../../schemas/reminder.schema";

export function useCreateReminder(applicationId: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (values: ReminderFormValues) => reminderService.create(applicationId, values),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: reminderKeys.all }),
  });
}
