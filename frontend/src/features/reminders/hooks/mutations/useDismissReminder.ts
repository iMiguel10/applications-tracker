import { useMutation, useQueryClient } from "@tanstack/react-query";
import { reminderKeys } from "../../reminder.keys";
import { reminderService } from "../../services/reminder.service";

export function useDismissReminder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: reminderService.dismiss,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: reminderKeys.all }),
  });
}
