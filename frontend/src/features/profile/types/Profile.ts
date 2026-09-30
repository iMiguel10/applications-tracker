export interface ProfileLink {
  label: string;
  url: string;
}

/** Datos de contacto y resumen del CV (RF-100). Un perfil que nunca se ha
 * guardado llega con todo a `null` y sin enlaces. */
export interface Profile {
  full_name: string | null;
  headline: string | null;
  contact_email: string | null;
  phone: string | null;
  location: string | null;
  links: ProfileLink[];
  summary: string | null;
}

export const MAX_LINKS = 10;
export const SUMMARY_MAX_LENGTH = 2000;
