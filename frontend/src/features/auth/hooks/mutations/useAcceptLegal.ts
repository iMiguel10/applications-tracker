import { useMutation, useQueryClient } from "@tanstack/react-query";

import type { Me } from "../../types/Auth";
import { authKeys } from "../../auth.keys";
import { authService } from "../../services/auth.service";

/** Acepta los términos y la privacidad vigentes (issue #3) y lo apunta en la caché de
 * `GET /me`, que no se vuelve a pedir durante la sesión. */
export function useAcceptLegal() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (version: string) => authService.acceptLegal(version),
    onSuccess: (_result, version) => {
      queryClient.setQueryData<Me>(authKeys.me(), (me) =>
        me ? { ...me, legal_accepted_version: version } : me,
      );
    },
  });
}
