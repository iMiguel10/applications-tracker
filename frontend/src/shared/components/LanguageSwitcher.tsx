import { Languages } from "lucide-react";
import { useTranslation } from "react-i18next";

import { chooseBrowserLanguage, SUPPORTED_LANGUAGES } from "@/shared/i18n/i18n";
import { cn } from "@/shared/lib/utils";

/** Idioma de las pantallas de acceso (sin sesión, así que sin preferencia de
 * cuenta). Se recuerda en el navegador; dentro de la aplicación manda la cuenta. */
export function LanguageSwitcher({ className }: { className?: string }) {
  const { t, i18n } = useTranslation();
  const current = i18n.resolvedLanguage;

  return (
    <div
      role="group"
      aria-label={t("nav.language")}
      className={cn("inline-flex items-center gap-1 text-sm", className)}
    >
      <Languages className="mr-1 size-4 text-muted-foreground" aria-hidden />
      {SUPPORTED_LANGUAGES.map((language) => (
        <button
          key={language}
          type="button"
          lang={language}
          aria-pressed={current === language}
          onClick={() => void chooseBrowserLanguage(language)}
          className={cn(
            "rounded-md px-2 py-1 text-muted-foreground outline-none hover:bg-muted hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50",
            current === language && "bg-muted font-medium text-foreground",
          )}
        >
          {t(`preferences.language.${language}`)}
        </button>
      ))}
    </div>
  );
}
