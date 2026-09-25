import { useMutation, useQueryClient } from "@tanstack/react-query";
import { authKeys } from "../../auth.keys";
import { authService } from "../../services/auth.service";

export function useSendVerificationEmail() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: authService.sendVerificationEmail,
    onSuccess: (result) => {
      // Ya estaba verificado (quizá desde otro dispositivo): el aviso sobra.
      if (result === "already_verified") {
        void queryClient.invalidateQueries({ queryKey: authKeys.emailVerified() });
      }
    },
  });
}
