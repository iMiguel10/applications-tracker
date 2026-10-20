/**
 * Páginas del manual de uso que enlaza la aplicación (issue #6), con su ruta dentro
 * del manual (Docusaurus, `manual/docs/`, sin extensión). Es la única lista: ninguna
 * página escribe una ruta del manual a mano. El manual comprueba en su CI que cada
 * una existe en los dos idiomas (`manual/scripts/check-help-links.mjs`): renombrar
 * una página del manual sin tocar esta lista hace fallar la CI.
 */
export const MANUAL_PAGES = {
  home: "",
  registerApplication: "uso/registrar-una-solicitud",
  findApplications: "uso/encontrar-solicitudes",
  statusChanges: "uso/seguir-el-estado",
  board: "uso/tablero",
  interviews: "uso/entrevistas",
  reminders: "uso/recordatorios",
  calendar: "uso/calendario",
  dashboard: "uso/dashboard",
  documents: "uso/documentos",
  profile: "uso/perfil",
  generateCv: "uso/generar-un-cv",
  aiCv: "uso/adaptar-el-cv-con-ia",
  aiCoverLetter: "uso/escribir-una-carta-con-ia",
  ownAiKey: "uso/usar-tu-propia-clave-de-ia",
  preferences: "uso/preferencias",
  deleteAccount: "uso/borrar-la-cuenta",
} as const;

export type ManualPage = keyof typeof MANUAL_PAGES;
