import { apiClient } from "@/shared/lib/apiClient";
import type { LibraryDocument } from "@/features/documents/types/Document";
import type {
  AiConsents,
  AiProposal,
  AiProvider,
  AiTask,
  ProposalLanguage,
  ReviewedCvProposal,
} from "../types/Ai";

const proposals = (applicationId: string) => `/applications/${applicationId}/ai-proposals`;

export const aiService = {
  consents: () => apiClient.get<AiConsents>("/ai/consents"),

  grantConsent: (provider: AiProvider) => apiClient.put<AiConsents>(`/ai/consents/${provider}`),

  revokeConsent: (provider: AiProvider) => apiClient.delete<void>(`/ai/consents/${provider}`),

  listProposals: (applicationId: string) => apiClient.get<AiProposal[]>(proposals(applicationId)),

  getProposal: (applicationId: string, proposalId: string) =>
    apiClient.get<AiProposal>(`${proposals(applicationId)}/${proposalId}`),

  /** Responde enseguida con la propuesta en cola: el `worker` llama a la IA (A35). */
  requestProposal: (applicationId: string, kind: AiTask, language: ProposalLanguage) =>
    apiClient.post<AiProposal>(proposals(applicationId), { kind, language }),

  /** El PDF con la propuesta revisada (RF-113), como un CV generado más. */
  createDocument: (
    applicationId: string,
    proposalId: string,
    input: { design: string; name: string | null; proposal: ReviewedCvProposal },
  ) =>
    apiClient.post<LibraryDocument>(
      `${proposals(applicationId)}/${proposalId}/document`,
      input,
    ),
};
