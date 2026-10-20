import type { AiProvider } from "@/features/ai/types/Ai";

/** Lo que necesitan las páginas legales (issue #3): el responsable de los datos y lo
 * que la instalación tiene activo. */
export interface LegalInfo {
  /** Sin nombre y contacto del responsable: uso personal, sin enlaces ni aceptación. */
  configured: boolean;
  /** Versión vigente de los términos y la política de privacidad. */
  version: string;
  operator_name: string | null;
  contact_email: string | null;
  address: string | null;
  tax_id: string | null;
  /** Autoridad de control; `null`, la española (AEPD). */
  supervisory_authority: string | null;
  ai_platform_provider: AiProvider | null;
  ai_own_key_providers: AiProvider[];
  /** Días, como mucho, que un dato borrado sigue en las copias. */
  backup_retention_days: number;
}

/** Capacidades de la instalación (`GET /meta`, público). */
export interface Meta {
  /** Sin SMTP no se envían emails: no hay recuperación de contraseña. */
  email_enabled: boolean;
  /** Registro cerrado (decisión 0022): las cuentas las crea quien administra. */
  signup_enabled: boolean;
  /** Tamaño máximo de un PDF subido, en bytes: se avisa antes de subirlo. */
  max_document_bytes: number;
  legal: LegalInfo;
}
