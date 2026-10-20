/** Las páginas legales de la instalación (issue #3), en `/legal/<página>`. Públicas:
 * se leen sin sesión, también antes de tener cuenta. */
export const LEGAL_PAGES = ["notice", "privacy", "terms", "cookies"] as const;

export type LegalPage = (typeof LEGAL_PAGES)[number];

export const legalPath = (page: LegalPage) => `/legal/${page}`;

export function isLegalPage(value: string | undefined): value is LegalPage {
  return (LEGAL_PAGES as readonly string[]).includes(value ?? "");
}
