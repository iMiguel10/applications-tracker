export const LIMIT_KEYS = ["applications", "companies", "reminders"] as const;
export type LimitKey = (typeof LIMIT_KEYS)[number];

export interface LimitUsage {
  key: LimitKey;
  used: number;
  /** `null`: esta cuenta no tiene límite en este recurso (excepción individual). */
  limit: number | null;
  remaining: number | null;
  /** Ningún límite actual se renueva. */
  renews: boolean;
}

/** `GET /me/usage` (RF-141). */
export interface Usage {
  limits: LimitUsage[];
  /** Fracción (`used / limit`) a partir de la que se avisa (RF-144). */
  warning_ratio: number;
}
