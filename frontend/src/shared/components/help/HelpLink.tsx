import { CircleHelp } from "lucide-react";
import { useTranslation } from "react-i18next";

import type { ManualPage } from "@/shared/config/manualPages";
import { manualUrl } from "@/shared/lib/manual";
import { buttonVariants } from "@/shared/components/ui/button";
import { cn } from "@/shared/lib/utils";

/**
 * Ayuda en contexto (issue #6): un "?" discreto que abre la página del manual de
 * ese sitio, en el idioma de la interfaz y en otra pestaña (así no se pierde lo que
 * se estaba escribiendo). El texto accesible dice de qué es la ayuda y que se abre
 * aparte; se ve también como tooltip nativo al pasar el ratón.
 */
export function HelpLink({ page, className }: { page: ManualPage; className?: string }) {
  const { t, i18n } = useTranslation();
  const label = `${t(`help.pages.${page}`)} ${t("help.newTab")}`;

  return (
    <a
      href={manualUrl(page, i18n.resolvedLanguage)}
      target="_blank"
      rel="noopener"
      aria-label={label}
      title={t(`help.pages.${page}`)}
      className={cn(
        buttonVariants({ variant: "ghost", size: "icon-sm" }),
        "text-muted-foreground hover:text-foreground",
        className,
      )}
    >
      <CircleHelp aria-hidden="true" />
    </a>
  );
}
