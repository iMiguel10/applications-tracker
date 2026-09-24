import { useMutation } from "@tanstack/react-query";
import { authService } from "../../services/auth.service";

export function useSendPasswordResetEmail() {
  return useMutation({ mutationFn: authService.sendPasswordResetEmail });
}
