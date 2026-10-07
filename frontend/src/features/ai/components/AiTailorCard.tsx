import { useState } from "react";
import { Languages, Loader2, Sparkles } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { toast } from "sonner";

import { errorMessageKey, errorMessageParams } from "@/shared/lib/errors";
import { formatDateTime } from "@/shared/lib/format";
import { Button, buttonVariants } from "@/shared/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { ListSkeleton } from "@/shared/components/common/Skeletons";
import { ViewToggle } from "@/shared/components/common/ViewToggle";
import { useAccountZone } from "@/features/auth/hooks/useAccountZone";
import { uiCvLanguage } from "@/features/documents/lib/designName";
import { useUsage } from "@/features/usage/hooks/queries/useUsage";
import type { ApplicationDetail } from "@/features/applications/types/Application";
import { useGrantAiConsent } from "../hooks/mutations/useGrantAiConsent";
import { useRequestAiProposal } from "../hooks/mutations/useRequestAiProposal";
import { useAiConsents } from "../hooks/queries/useAiConsents";
import { isInFlight, useAiProposals } from "../hooks/queries/useAiProposals";
import { providerName } from "../lib/providers";
import type { AiProposal, ProposalLanguage } from "../types/Ai";
import { AiConsentDialog } from "./AiConsentDialog";

/** Igual que el backend (MIN_JOB_DESCRIPTION_LENGTH): más corta, no se pide. */
export const MIN_JOB_DESCRIPTION_LENGTH = 200;
// Las propuestas que se enseñan en la tarjeta: las más recientes.
const SHOWN = 3;

/**
 * Adaptar el CV a la oferta con IA (RF-110): pedir la propuesta, ver cómo va y
 * entrar a revisarla. Explica antes de pedirla por qué no se puede (sin oferta,
 * oferta corta, sin usos) y pide el consentimiento la primera vez (RF-116).
 */
export function AiTailorCard({ application }: { application: ApplicationDetail }) {
  const { t, i18n } = useTranslation();
  const consents = useAiConsents();
  const proposals = useAiProposals(application.id);
  const usage = useUsage();
  const grant = useGrantAiConsent();
  const request = useRequestAiProposal(application.id);
  const [language, setLanguage] = useState<ProposalLanguage>(uiCvLanguage(i18n.language));
  const [consentOpen, setConsentOpen] = useState(false);

  if (consents.isLoading) return null;
  const provider = consents.data?.platform_provider ?? null;
  // Sin IA en esta instalación, la tarjeta no se ofrece (las claves propias llegan
  // en el paso 5 de F15).
  if (!provider) return null;

  const description = (application.job_description ?? "").trim();
  const quota = usage.data?.limits.find((item) => item.key === "ai_cv_proposals");
  const remaining = quota?.remaining ?? null;
  const consented = !!consents.data?.consents.find(
    (consent) => consent.provider === provider && consent.granted,
  );
  const busy = !!proposals.data?.some(isInFlight) || request.isPending;

  const blocked = !description
    ? "noDescription"
    : description.length < MIN_JOB_DESCRIPTION_LENGTH
      ? "shortDescription"
      : // Mientras una está en curso ya cuenta como gastada: no se dice hasta que acaba.
        remaining === 0 && !busy
        ? "noUses"
        : null;

  const ask = () =>
    request.mutate(
      { kind: "cv", language },
      { onError: (error) => toast.error(t(errorMessageKey(error), errorMessageParams(error))) },
    );

  const start = () => (consented ? ask() : setConsentOpen(true));

  const accept = () =>
    grant.mutate(provider, {
      onSuccess: () => {
        setConsentOpen(false);
        ask();
      },
      onError: (error) => toast.error(t(errorMessageKey(error), errorMessageParams(error))),
    });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="size-4 text-primary" aria-hidden />
          {t("ai.tailor.title")}
        </CardTitle>
        <CardDescription>{t("ai.tailor.description")}</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        {blocked === "noDescription" && (
          <p className="text-sm text-muted-foreground">
            {t("ai.tailor.noDescription")}{" "}
            <Link
              to={`/applications/${application.id}/edit`}
              className="underline underline-offset-2 hover:text-foreground"
            >
              {t("applications.addJobDescription")}
            </Link>
          </p>
        )}
        {blocked === "shortDescription" && (
          <p className="text-sm text-muted-foreground">
            {t("ai.tailor.shortDescription", { min: MIN_JOB_DESCRIPTION_LENGTH })}
          </p>
        )}
        {blocked === "noUses" && (
          <p className="text-sm text-muted-foreground">{t("ai.tailor.noUses")}</p>
        )}

        {!blocked && !(remaining === 0 && busy) && (
          <div className="flex flex-wrap items-center gap-3">
            <Button onClick={start} disabled={busy}>
              {busy ? <Loader2 className="animate-spin" /> : <Sparkles />}
              {t("ai.tailor.request")}
            </Button>
            <ViewToggle<ProposalLanguage>
              label={t("ai.tailor.language")}
              options={(["es", "en"] as const).map((value) => ({
                value,
                label: t(`ai.tailor.languages.${value}`),
                icon: Languages,
              }))}
              value={language}
              onChange={setLanguage}
            />
          </div>
        )}
        {remaining !== null && remaining > 0 && (
          <p className="-mt-2 text-xs text-muted-foreground">
            {t("ai.tailor.freeUses", { count: remaining, provider: providerName(provider) })}
          </p>
        )}

        {proposals.isLoading && <ListSkeleton rows={1} />}
        {proposals.data && proposals.data.length > 0 && (
          <ul className="grid gap-2" aria-label={t("ai.tailor.history")}>
            {proposals.data.slice(0, SHOWN).map((proposal) => (
              <ProposalRow key={proposal.id} proposal={proposal} />
            ))}
          </ul>
        )}
      </CardContent>

      <AiConsentDialog
        provider={provider}
        open={consentOpen}
        onOpenChange={setConsentOpen}
        onAccept={accept}
        accepting={grant.isPending || request.isPending}
      />
    </Card>
  );
}

function ProposalRow({ proposal }: { proposal: AiProposal }) {
  const { t, i18n } = useTranslation();
  const zone = useAccountZone();
  const when = formatDateTime(proposal.created_at, i18n.language, zone);

  return (
    <li className="flex flex-wrap items-center justify-between gap-2 rounded-lg border bg-card p-3 text-sm">
      <div className="grid gap-0.5">
        <span className="font-medium">
          {isInFlight(proposal) ? (
            <span className="inline-flex items-center gap-1.5">
              <Loader2 className="size-3.5 animate-spin" aria-hidden />
              {t("ai.status.running")}
            </span>
          ) : proposal.status === "succeeded" ? (
            t("ai.status.succeeded")
          ) : (
            t(`ai.errors.${proposal.error_code ?? "ai_interrupted"}`)
          )}
        </span>
        <span className="text-xs text-muted-foreground">
          {when} · {proposal.model}
        </span>
      </div>
      {proposal.status === "succeeded" && (
        <Link
          to={`/applications/${proposal.application_id}/ai/${proposal.id}`}
          className={buttonVariants({ variant: "outline", size: "sm" })}
        >
          {t("ai.tailor.review")}
        </Link>
      )}
    </li>
  );
}
