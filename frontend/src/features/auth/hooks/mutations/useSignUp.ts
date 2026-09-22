import { useMutation, useQueryClient } from "@tanstack/react-query";
import { authService } from "../../services/auth.service";

export function useSignUp() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: authService.signUp,
    onSuccess: (result) => {
      if (result.status === "ok") queryClient.clear();
    },
  });
}
