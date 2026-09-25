import { useEffect, useRef } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { authKeys } from "../../auth.keys";
import { browserTimezone } from "../../lib/timezones";
import { preferencesService } from "../../services/preferences.service";
import type { Preferences } from "../../types/Auth";

/**
 * Si la cuenta no tiene zona horaria, envía la del navegador (RF-07, A39). Cubre a
 * la vez las cuentas nuevas y las anteriores a F11, sin preguntar nada. Una sola vez
 * por carga: si el backend no conoce la zona (422), la cuenta se queda sin ella (UTC)
 * y el usuario puede elegirla en Preferencias.
 */
export function useDetectTimezone(preferences: Preferences | undefined) {
  const queryClient = useQueryClient();
  const attempted = useRef(false);
  const { mutate } = useMutation({
    mutationFn: preferencesService.setTimezone,
    onSuccess: (data) => queryClient.setQueryData(authKeys.preferences(), data),
  });

  useEffect(() => {
    if (!preferences || preferences.timezone !== null || attempted.current) return;
    const timezone = browserTimezone();
    if (!timezone) return;
    attempted.current = true;
    mutate(timezone);
  }, [preferences, mutate]);
}
