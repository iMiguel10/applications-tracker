import { CircleHelp } from "lucide-react";
import { useTranslation } from "react-i18next";

import { manualUrl } from "@/shared/lib/manual";
import { cn } from "@/shared/lib/utils";

/**
 * Enlace general **Ayuda** (issue #6): la portada del manual de uso en el idioma de
 * la interfaz, en otra pestaña. Va en el menú de la cuenta (escritorio y móvil) y en
 * las pantallas de acceso, para quien aún no ha entrado. Los estilos los pone quien
 * lo coloca, para que se parezca a lo que tiene al lado.
 */
export function ManualLink({ className }: { className?: string }) {
  const { t, i18n } = useTranslation();

  return (
    <a
      href={manualUrl("home", i18n.resolvedLanguage)}
      target="_blank"
      rel="noopener"
      className={cn("flex items-center gap-2", className)}
    >
      <CircleHelp className="size-4" aria-hidden="true" />
      {t("help.link")}
      {" "}
      <span className="sr-only">{t("help.newTab")}</span>
    </a>
  );
}
