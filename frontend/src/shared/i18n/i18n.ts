import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

import es from "./locales/es.json";
import en from "./locales/en.json";

// `<html lang>` sigue al idioma de la interfaz: los lectores de pantalla eligen la
// pronunciación por él (index.html arranca con "es").
i18n.on("languageChanged", (language) => {
  document.documentElement.lang = language;
});

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      es: { translation: es },
      en: { translation: en },
    },
    fallbackLng: "es",
    supportedLngs: ["es", "en"],
    interpolation: {
      escapeValue: false,
    },
    detection: {
      order: ["localStorage", "navigator"],
      caches: ["localStorage"],
    },
  });

export const SUPPORTED_LANGUAGES = ["es", "en"] as const;
export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number];

// Idioma elegido a mano en ESTE navegador (selector de las pantallas de acceso).
// Va aparte de la caché de i18next ("i18nextLng"), que también guarda el idioma de
// la cuenta y que se vacía cuando la cuenta vuelve a "seguir el navegador".
const BROWSER_CHOICE_KEY = "browserLanguage";

function isSupported(value: string | null | undefined): value is SupportedLanguage {
  return (SUPPORTED_LANGUAGES as readonly string[]).includes(value ?? "");
}

/** El idioma "del navegador": el elegido en el selector de acceso si lo hay; si
 * no, el del sistema. Es lo que sigue una cuenta con el idioma sin fijar. */
export function browserLanguage(): SupportedLanguage {
  try {
    const chosen = localStorage.getItem(BROWSER_CHOICE_KEY);
    if (isSupported(chosen)) return chosen;
  } catch {
    // Almacenamiento bloqueado (modo privado estricto): se usa el del sistema.
  }
  const short = navigator.language.split("-")[0];
  return isSupported(short) ? short : "es";
}

/** Cambia el idioma desde las pantallas de acceso y lo recuerda en el navegador. */
export function chooseBrowserLanguage(language: SupportedLanguage): Promise<unknown> {
  try {
    localStorage.setItem(BROWSER_CHOICE_KEY, language);
  } catch {
    // Sin almacenamiento el cambio vale para esta visita.
  }
  return i18n.changeLanguage(language);
}

export default i18n;