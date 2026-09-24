/** Capacidades de la instalación (`GET /meta`, público). */
export interface Meta {
  /** Sin SMTP no se envían emails: no hay recuperación de contraseña. */
  email_enabled: boolean;
}
