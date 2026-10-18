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
// La fuente desde JS y no con @import en global.css: el plugin de PostCSS de
// Tailwind la inlinea sin reescribir sus url(./files/…) y en el build de
// producción los .woff2 daban 404 (la interfaz salía con la fuente del sistema).
import "@fontsource-variable/geist";
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
