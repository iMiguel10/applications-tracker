import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { cn } from "@/shared/lib/utils";
import { useMeta } from "@/features/meta/hooks/queries/useMeta";
import { LEGAL_PAGES, legalPath } from "../lib/legalPages";

/**
 * Enlaces a las páginas legales (issue #3), para las pantallas de acceso y el pie de
 * la aplicación. Solo si la instalación las tiene configuradas: una de uso personal
 * no las necesita (decisión 0026), aunque sigan existiendo en su URL.
 */
export function LegalLinks({ className }: { className?: string }) {
  const { t } = useTranslation();
  const { data: meta } = useMeta();
  if (!meta?.legal.configured) return null;

  return (
    <nav aria-label={t("legal.nav.label")} className={cn("text-xs", className)}>
      <ul className="flex flex-wrap gap-x-4 gap-y-1">
        {LEGAL_PAGES.map((page) => (
          <li key={page}>
            <Link
              to={legalPath(page)}
              className="text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
            >
              {t(`legal.nav.${page}`)}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
