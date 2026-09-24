import { QueryClient } from "@tanstack/react-query";

import { ApiError } from "./apiClient";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutos
      gcTime: 1000 * 60 * 30,   // 30 minutos
      // Un 4xx (p. ej. el 404 de una solicitud que no existe) no se arregla
      // reintentando: solo se reintenta una vez ante fallos de red o 5xx.
      retry: (failureCount, error) =>
        !(error instanceof ApiError && error.status < 500) && failureCount < 1,
      refetchOnWindowFocus: false
    },
    mutations: {
      retry: 0
    }
  }
});
