import { useEffect, useMemo, useRef } from "react";
import { type Query, useQueries, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { useMe } from "@/features/auth/hooks/queries/useMe";
import { usageKeys } from "@/features/usage/usage.keys";
import { aiKeys } from "../ai.keys";
import { isInFlight, PROPOSAL_POLL_MS } from "../hooks/queries/useAiProposals";
import {
  PROPOSAL_TOAST_MS,
  reviewPath,
  unwatchProposal,
  useWatchedProposals,
} from "../lib/watchedProposals";
import { aiService } from "../services/ai.service";
import type { AiProposal } from "../types/Ai";

/**
 * Avisa, en cualquier página, cuando termina una propuesta de IA que se pidió en
 * esta pestaña: lista para revisar o por qué no salió. No avisa en la propia página
 * de revisión, que ya lo enseña. Sin propuestas vigiladas no hace ninguna petición.
 */
export function AiProposalWatcher() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const queryClient = useQueryClient();
  const { data: me } = useMe();
  const watched = useWatchedProposals();
  const mine = useMemo(
    () => (me ? watched.filter((item) => item.userId === me.id) : []),
    [me, watched],
  );

  // Las de otra cuenta (se cerró sesión en esta pestaña) no se consultan.
  useEffect(() => {
    if (!me) return;
    watched
      .filter((item) => item.userId !== me.id)
      .forEach((item) => unwatchProposal(item.proposalId));
  }, [me, watched]);

  // La misma clave que la página de revisión: comparten la respuesta.
  const results = useQueries({
    queries: mine.map((item) => ({
      queryKey: aiKeys.proposal(item.applicationId, item.proposalId),
      queryFn: () => aiService.getProposal(item.applicationId, item.proposalId),
      refetchInterval: (query: Query<AiProposal>) =>
        query.state.data && !isInFlight(query.state.data) ? false : PROPOSAL_POLL_MS,
      retry: false,
    })),
  });

  // Un aviso por propuesta, aunque el efecto se repita antes de que se borre.
  const notified = useRef(new Set<string>());

  useEffect(() => {
    mine.forEach((item, index) => {
      const result = results[index];
      if (result?.isError) {
        // Ya no existe (o no es de esta cuenta): nada que avisar.
        unwatchProposal(item.proposalId);
        return;
      }
      const proposal = result?.data;
      if (!proposal || isInFlight(proposal) || notified.current.has(item.proposalId)) return;
      notified.current.add(item.proposalId);
      unwatchProposal(item.proposalId);
      // La tarjeta de la solicitud y los usos gratuitos cambian al terminar.
      void queryClient.invalidateQueries({
        queryKey: aiKeys.proposals(item.applicationId),
        // Solo la lista: la de esta propuesta ya está al día.
        exact: true,
      });
      void queryClient.invalidateQueries({ queryKey: usageKeys.all });

      const review = reviewPath(item.applicationId, item.proposalId);
      if (pathname === review) return;
      const params = { position: item.position, company: item.company };
      if (proposal.status === "succeeded") {
        toast.success(t(`ai.notify.ready.${item.kind}`, params), {
          duration: PROPOSAL_TOAST_MS,
          action: { label: t("ai.notify.review"), onClick: () => void navigate(review) },
        });
      } else {
        toast.error(t(`ai.notify.failed.${item.kind}`, params), {
          description: t(`ai.errors.${proposal.error_code ?? "ai_interrupted"}`),
          duration: PROPOSAL_TOAST_MS,
          action: {
            label: t("ai.notify.openApplication"),
            onClick: () => void navigate(`/applications/${item.applicationId}`),
          },
        });
      }
    });
  }, [mine, results, pathname, navigate, queryClient, t]);

  return null;
}
