import { redirect, type LoaderFunctionArgs } from "react-router-dom";
import { authService } from "@/features/auth/services/auth.service";

/** Rutas protegidas: sin sesión, al login recordando a dónde se quería ir. */
export async function requireAuthLoader({ request }: LoaderFunctionArgs) {
  if (!(await authService.sessionExists())) {
    const url = new URL(request.url);
    throw redirect(`/login?redirect=${encodeURIComponent(url.pathname + url.search)}`);
  }
  return null;
}

/** Login y registro: con sesión ya iniciada no tiene sentido mostrarlos. */
export async function redirectIfAuthenticatedLoader() {
  if (await authService.sessionExists()) {
    throw redirect("/applications");
  }
  return null;
}
