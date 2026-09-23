// PRIMERO: inicializa SuperTokens antes de que nada pueda lanzar peticiones.
import "./shared/lib/supertokens";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";

import { queryClient } from "@/shared/lib/queryClient";
import { ThemeProvider } from "@/app/providers/ThemeProvider";

import App from "./App.tsx";

import "./shared/i18n/i18n";
import "./styles/global.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <App />
        <ReactQueryDevtools initialIsOpen={false} />
      </QueryClientProvider>
    </ThemeProvider>
  </StrictMode>,
);
