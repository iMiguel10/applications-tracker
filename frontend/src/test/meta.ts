import type { LegalInfo, Meta } from "@/features/meta/types/Meta";

/** Una instalación sin textos legales (uso personal), para las pruebas. */
export const NO_LEGAL: LegalInfo = {
  configured: false,
  version: "2026-10-20",
  operator_name: null,
  contact_email: null,
  address: null,
  tax_id: null,
  supervisory_authority: null,
  ai_platform_provider: null,
  ai_own_key_providers: [],
  backup_retention_days: 35,
};

/** Una instalación con su responsable configurado (issue #3). */
export const SOME_LEGAL: LegalInfo = {
  ...NO_LEGAL,
  configured: true,
  operator_name: "Ana García",
  contact_email: "privacidad@example.com",
};

/** `GET /meta` con valores por defecto: correo y registro activos, sin textos legales. */
export function makeMeta(overrides: Partial<Meta> = {}): Meta {
  return {
    email_enabled: true,
    signup_enabled: true,
    max_document_bytes: 5 * 1024 * 1024,
    legal: NO_LEGAL,
    ...overrides,
  };
}
