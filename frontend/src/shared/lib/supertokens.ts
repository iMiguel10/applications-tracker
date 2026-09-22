import SuperTokens from "supertokens-web-js";
import EmailPassword from "supertokens-web-js/recipe/emailpassword";
import Session from "supertokens-web-js/recipe/session";

import { queryClient } from "./queryClient";

const PUBLIC_PATHS = ["/login", "/register"];

// Se ejecuta al importar este módulo, que main.tsx importa ANTES que nada: el SDK
// intercepta fetch para añadir cabeceras y refrescar la sesión ante un 401. Una
// petición lanzada antes de init() saldría sin interceptar (autenticacion.md §4).
SuperTokens.init({
  appInfo: {
    appName: "Applications Tracker",
    apiDomain: import.meta.env.VITE_API_URL,
    apiBasePath: "/auth",
  },
  recipeList: [
    Session.init({
      onHandleEvent: (event) => {
        // La caché de TanStack Query sobrevive al cambio de usuario: sin esto, el
        // siguiente usuario del navegador vería datos del anterior (prueba T8).
        if (event.action === "SIGN_OUT" || event.action === "UNAUTHORISED") {
          queryClient.clear();
        }

        // Sesión irrecuperable (el SDK ya intentó refrescar): al login, salvo que ya
        // estemos en una página pública.
        if (event.action === "UNAUTHORISED" && !PUBLIC_PATHS.includes(window.location.pathname)) {
          const redirect = window.location.pathname + window.location.search;
          window.location.assign(`/login?redirect=${encodeURIComponent(redirect)}`);
        }
      },
    }),
    EmailPassword.init(),
  ],
});
