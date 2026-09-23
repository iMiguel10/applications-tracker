import { useMutation, useQueryClient } from "@tanstack/react-query";
import { reminderKeys } from "../../reminder.keys";
import { reminderService } from "../../services/reminder.service";

export function useCompleteReminder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: reminderService.complete,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: reminderKeys.all }),
  });
}
