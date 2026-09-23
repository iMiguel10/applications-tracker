import { useLayoutEffect } from "react";

import { useTheme } from "./useTheme";

/** Para páginas que deben verse siempre en claro pase lo que pase con el tema elegido
 * (login/registro, ver `ThemeProvider`): pide "forzar claro" mientras el componente
 * que lo llama está montado, y lo suelta al desmontarse. */
export function useForceLightTheme() {
  const { setForceLight } = useTheme();

  useLayoutEffect(() => {
    setForceLight(true);
    return () => setForceLight(false);
  }, [setForceLight]);
}
