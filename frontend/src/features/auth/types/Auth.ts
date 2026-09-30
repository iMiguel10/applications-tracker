export interface Me {
  id: string;
  email: string | null;
}

export const LANGUAGES = ["es", "en"] as const;
export type Language = (typeof LANGUAGES)[number];

export interface Preferences {
  /** `null`: sigue el idioma del navegador. */
  language: Language | null;
  stale_after_days: number;
  /** Zona IANA ("Europe/Madrid"); `null` hasta que se detecta del navegador. */
  timezone: string | null;
  /** F12 (RF-84): avisos por email, cada uno por separado. */
  notify_reminder_due: boolean;
  notify_interview: boolean;
  notify_weekly_digest: boolean;
  notify_stale: boolean;
  /** RF-80: horas de antelación del aviso de recordatorio; 0 = al vencer. */
  reminder_notice_hours: number;
  /** RF-81: horas de antelación del aviso de entrevista. */
  interview_notice_hours: number;
}

export type AuthField = "email" | "password";

/**
 * Resultado cerrado de login y registro. Traduce los estados del SDK de
 * SuperTokens para que los componentes no dependan de sus nombres.
 */
export type AuthResult =
  | { status: "ok" }
  | { status: "wrong_credentials" }
  | { status: "field_errors"; fields: AuthField[] }
  | { status: "error" };

/** Resultado de guardar la contraseña nueva con el enlace del email. */
export type ResetPasswordResult =
  | { status: "ok" }
  /** Enlace ya usado, caducado o manipulado: hay que pedir otro. */
  | { status: "invalid_link" }
  /** No cumple la política de contraseñas del backend (invariante 7). */
  | { status: "password_policy" }
  | { status: "error" };
