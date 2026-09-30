/** Capacidades de la instalación (`GET /meta`, público). */
export interface Meta {
  /** Sin SMTP no se envían emails: no hay recuperación de contraseña. */
  email_enabled: boolean;
  /** Tamaño máximo de un PDF subido, en bytes: se avisa antes de subirlo. */
  max_document_bytes: number;
}
