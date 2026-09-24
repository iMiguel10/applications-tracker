import { useEffect } from "react";
import { useTranslation } from "react-i18next";

/** Título de la pestaña por página (WCAG 2.4.2): en una SPA no cambia solo al navegar,
 * y es lo primero que anuncia un lector de pantalla. Sin título (aún cargando), queda
 * solo el nombre de la app. */
export function useDocumentTitle(title?: string) {
  const { t } = useTranslation();
  const appName = t("app.name");

  useEffect(() => {
    document.title = title ? `${title} · ${appName}` : appName;
  }, [title, appName]);
}
