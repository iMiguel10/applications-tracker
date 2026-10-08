import { apiClient } from "@/shared/lib/apiClient";
import type { LibraryDocument } from "@/features/documents/types/Document";
import type {
  AiConsents,
  AiKeys,
  AiProposal,
  AiProvider,
  AiTask,
  ProposalLanguage,
  ReviewedCoverLetter,
  ReviewedCvProposal,
} from "../types/Ai";

/** Lo que se envía al generar el PDF: el CV revisado o la carta revisada, según el
 * tipo de la propuesta. */
export type AiDocumentInput = { design: string; name: string | null } & (
  | { proposal: ReviewedCvProposal }
  | { letter: ReviewedCoverLetter }
);

const proposals = (applicationId: string) => `/applications/${applicationId}/ai-proposals`;

export const aiService = {
  consents: () => apiClient.get<AiConsents>("/ai/consents"),

  grantConsent: (provider: AiProvider) => apiClient.put<AiConsents>(`/ai/consents/${provider}`),

  revokeConsent: (provider: AiProvider) => apiClient.delete<void>(`/ai/consents/${provider}`),

  keys: () => apiClient.get<AiKeys>("/ai/keys"),

  /** Se comprueba con el proveedor antes de guardarla, cifrada; queda activa. */
  saveKey: (provider: AiProvider, apiKey: string, model: string | null) =>
    apiClient.put<AiKeys>(`/ai/keys/${provider}`, { api_key: apiKey, model }),

  changeKeyModel: (provider: AiProvider, model: string) =>
    apiClient.patch<AiKeys>(`/ai/keys/${provider}`, { model }),

  deleteKey: (provider: AiProvider) => apiClient.delete<void>(`/ai/keys/${provider}`),

  /** null: volver a los usos gratuitos de la plataforma. */
  setActiveProvider: (provider: AiProvider | null) =>
    apiClient.put<AiKeys>("/ai/keys/active", { provider }),

  listProposals: (applicationId: string) => apiClient.get<AiProposal[]>(proposals(applicationId)),

  getProposal: (applicationId: string, proposalId: string) =>
    apiClient.get<AiProposal>(`${proposals(applicationId)}/${proposalId}`),

  /** Responde enseguida con la propuesta en cola: el `worker` llama a la IA (A35). */
  requestProposal: (applicationId: string, kind: AiTask, language: ProposalLanguage) =>
    apiClient.post<AiProposal>(proposals(applicationId), { kind, language }),

  /** El PDF con la propuesta revisada (RF-113), como un documento generado más. */
  createDocument: (applicationId: string, proposalId: string, input: AiDocumentInput) =>
    apiClient.post<LibraryDocument>(
      `${proposals(applicationId)}/${proposalId}/document`,
      input,
    ),
};
