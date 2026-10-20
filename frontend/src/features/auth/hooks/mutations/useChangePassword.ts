import { useMutation } from "@tanstack/react-query";
import { authService } from "../../services/auth.service";

export function useChangePassword() {
  return useMutation({
    mutationFn: ({ current, next }: { current: string; next: string }) =>
      authService.changePassword(current, next),
  });
}
