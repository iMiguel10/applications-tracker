/** `ollama` solo como IA de la plataforma, nunca con clave propia. */
export type AiProvider = "anthropic" | "openai" | "groq" | "ollama";
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
export interface ProfileReference {
  kind: "entry" | "bullet" | "skill" | "language";
  id: string;
}

/** Un requisito de la oferta. El porcentaje de encaje no lo da la IA: se calcula
 * aquí buscando `keywords` en el texto del CV (`lib/match.ts`). */
export interface Requirement {
  name: string;
  importance: RequirementImportance;
  keywords: string[];
  evidence: ProfileReference[];
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

/** Un párrafo de la carta con los elementos del perfil en que se apoya (ia.md §5). */
export interface LetterParagraph {
  text: string;
  sources: ProfileReference[];
}

/** La carta validada (RF-114). Nombre, contacto, fecha, empresa y puesto no salen
 * de la IA: los pone la plantilla. */
export interface CoverLetterProposal {
  greeting: string;
  paragraphs: LetterParagraph[];
  closing: string;
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
  /** `CvProposal` si `kind` es `cv`; `CoverLetterProposal` si es `cover_letter`. */
  proposal: CvProposal | CoverLetterProposal | null;
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

/** La carta tal como queda tras revisarla: lo que se envía al generar el PDF. */
export interface ReviewedCoverLetter {
  greeting: string;
  paragraphs: string[];
  closing: string;
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

/** Una clave propia guardada, sin la clave: nunca vuelve del servidor. */
export interface AiKey {
  model: string;
  last4: string;
  validated_at: string;
  /** false si quien despliega retiró ese modelo: hay que elegir otro. */
  model_allowed: boolean;
}

export interface AiProviderOption {
  provider: AiProvider;
  /** El primero es el recomendado. */
  models: string[];
  key: AiKey | null;
}

/** Claves propias (RF-151): con qué proveedores se puede usar una y cuál se usa. */
export interface AiKeys {
  own_keys_enabled: boolean;
  providers: AiProviderOption[];
  /** null: los usos gratuitos de la plataforma. */
  active_provider: AiProvider | null;
}
