import SuperTokens from "supertokens-web-js";
import EmailPassword from "supertokens-web-js/recipe/emailpassword";
import Session from "supertokens-web-js/recipe/session";

import i18n from "@/shared/i18n/i18n";
import { queryClient } from "./queryClient";

const PUBLIC_PATHS = ["/login", "/register", "/forgot-password", "/reset-password"];

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
      // Explícito aunque sea el valor por defecto: el backend acepta también
      // tokens en cabecera (decisión 0003), y el navegador debe usar SIEMPRE
      // cookies httpOnly, que JavaScript no puede leer (RNF-01).
      tokenTransferMethod: "cookie",
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
    EmailPassword.init({
      // Los emails que se piden sin sesión (recuperar la contraseña) salen en el
      // idioma de la cuenta o, si no lo tiene, en el de esta cabecera. Se envía el
      // de la interfaz, que puede no ser el del sistema si se eligió en el login.
      preAPIHook: async ({ url, requestInit }) => {
        const headers = new Headers(requestInit.headers);
        headers.set("Accept-Language", i18n.resolvedLanguage ?? i18n.language);
        return { url, requestInit: { ...requestInit, headers } };
      },
    }),
  ],
});
