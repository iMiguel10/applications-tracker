import { useEffect, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { usageKeys } from "@/features/usage/usage.keys";
import { aiKeys } from "../../ai.keys";
import { aiService } from "../../services/ai.service";
import { IN_FLIGHT_STATUSES, type AiProposal } from "../../types/Ai";

/** Cada cuánto se consulta mientras alguna propuesta se está generando (A35). */
export const PROPOSAL_POLL_MS = 2000;

export const isInFlight = (proposal: AiProposal) => IN_FLIGHT_STATUSES.includes(proposal.status);

/** Las propuestas de IA de una solicitud, las más recientes primero. Mientras
 * alguna esté en cola o en curso se vuelven a pedir hasta que termine. */
export function useAiProposals(applicationId: string) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: aiKeys.proposals(applicationId),
    queryFn: () => aiService.listProposals(applicationId),
    refetchInterval: (current) =>
      current.state.data?.some(isInFlight) ? PROPOSAL_POLL_MS : false,
  });

  // Al terminar una, el uso gratuito cambia: se gasta si el proveedor respondió y
  // se libera si falló antes (ia.md §6).
  const inFlight = query.data?.filter(isInFlight).length;
  const previous = useRef(inFlight);
  useEffect(() => {
    if (previous.current && inFlight !== undefined && inFlight < previous.current) {
      void queryClient.invalidateQueries({ queryKey: usageKeys.all });
    }
    previous.current = inFlight;
  }, [inFlight, queryClient]);

  return query;
}
