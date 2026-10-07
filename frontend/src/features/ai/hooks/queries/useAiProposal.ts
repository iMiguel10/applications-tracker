import { useQuery } from "@tanstack/react-query";
import { aiKeys } from "../../ai.keys";
import { aiService } from "../../services/ai.service";
import { isInFlight, PROPOSAL_POLL_MS } from "./useAiProposals";

export function useAiProposal(applicationId: string, proposalId: string) {
  return useQuery({
    queryKey: aiKeys.proposal(applicationId, proposalId),
    queryFn: () => aiService.getProposal(applicationId, proposalId),
    refetchInterval: (current) =>
      current.state.data && isInFlight(current.state.data) ? PROPOSAL_POLL_MS : false,
  });
}
