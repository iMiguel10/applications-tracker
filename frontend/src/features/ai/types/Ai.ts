export type AiProvider = "anthropic" | "openai" | "groq";
export type AiTask = "cv" | "cover_letter";
export type ProposalLanguage = "es" | "en";
export type ProposalStatus = "queued" | "running" | "succeeded" | "invalid" | "rejected" | "failed";
export type ProposalErrorCode =
  | "ai_provider_auth"
  | "ai_provider_quota"
  | "ai_provider_unavailable"
  | "ai_provider_rejected"
  | "ai_response_invalid"
  | "ai_response_refused"
  | "ai_offer_insufficient"
  | "profile_incomplete"
  | "ai_interrupted";

/** Mientras está así, la propuesta se consulta cada pocos segundos (A35). */
export const IN_FLIGHT_STATUSES: readonly ProposalStatus[] = ["queued", "running"];

export interface ProposedBullet {
  bullet_id: string;
  text: string;
}

export interface ProposedExperience {
  entry_id: string;
  bullets: ProposedBullet[];
}

export interface ProposedGap {
  requirement: string;
  note: string;
}

export type RequirementImportance = "required" | "preferred";

/** Un elemento del perfil que demuestra un requisito. `entry` es una experiencia,
 * formación, proyecto o certificación. */
export interface RequirementEvidence {
  kind: "entry" | "bullet" | "skill" | "language";
  id: string;
}

/** Un requisito de la oferta. El porcentaje de encaje no lo da la IA: se calcula
 * aquí buscando `keywords` en el texto del CV (`lib/match.ts`). */
export interface Requirement {
  name: string;
  importance: RequirementImportance;
  keywords: string[];
  evidence: RequirementEvidence[];
  /** Sin evidencia: por qué no aparece en el perfil. */
  note: string;
}

/** La propuesta validada (RF-110): solo referencias a elementos del perfil por id,
 * más los textos reescritos y las carencias (RF-112). */
export interface CvProposal {
  summary: string;
  experiences: ProposedExperience[];
  skill_ids: string[];
  gaps: ProposedGap[];
  /** Desde cv/v2; null en las propuestas anteriores, que no tienen encaje. */
  requirements?: Requirement[] | null;
}

export interface AiProposal {
  id: string;
  application_id: string;
  kind: AiTask;
  status: ProposalStatus;
  language: ProposalLanguage;
  key_source: "platform" | "user";
  provider: AiProvider;
  model: string;
  error_code: ProposalErrorCode | null;
  proposal: CvProposal | null;
  created_at: string;
  updated_at: string;
}

/** La propuesta tal como queda tras revisarla (RF-113): lo que se envía al
 * generar el PDF. */
export interface ReviewedCvProposal {
  summary: string;
  experiences: ProposedExperience[];
  skill_ids: string[];
}

export interface AiConsent {
  provider: AiProvider;
  granted: boolean;
  granted_at: string | null;
  revoked_at: string | null;
}

export interface AiConsents {
  text_version: number;
  /** A quién envía los datos el uso gratuito; `null`: la instalación no tiene IA. */
  platform_provider: AiProvider | null;
  platform_model: string | null;
  consents: AiConsent[];
}
