import { useMemo, useState } from "react";
import { AlertTriangle, ArrowLeft, Loader2, Sparkles } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";

import { useDocumentTitle } from "@/shared/hooks/useDocumentTitle";
import { errorMessageKey, errorMessageParams } from "@/shared/lib/errors";
import { Badge } from "@/shared/components/ui/badge";
import { DetailSkeleton } from "@/shared/components/common/Skeletons";
import { ErrorState } from "@/shared/components/common/ErrorState";
import { ApplicationLoadError } from "@/features/applications/components/ApplicationLoadError";
import { useApplication } from "@/features/applications/hooks/queries/useApplication";
import type { ApplicationDetail } from "@/features/applications/types/Application";
import { GenerateDocumentCard } from "@/features/ai/components/GenerateDocumentCard";
import { LetterReview } from "@/features/ai/components/LetterReview";
import { OfferMatchCard } from "@/features/ai/components/OfferMatchCard";
import { ProposalReview } from "@/features/ai/components/ProposalReview";
import { useCreateAiDocument } from "@/features/ai/hooks/mutations/useCreateAiDocument";
import { useAiProposal } from "@/features/ai/hooks/queries/useAiProposal";
import { isInFlight } from "@/features/ai/hooks/queries/useAiProposals";
import {
  letterFromProposal,
  letterProblem,
  toReviewedLetter,
  type LetterState,
} from "@/features/ai/lib/letter";
import { offerMatch, type CvSource } from "@/features/ai/lib/match";
import {
  reviewFromProposal,
  reviewProblem,
  toReviewedProposal,
  type ReviewState,
} from "@/features/ai/lib/review";
import type { AiDocumentInput } from "@/features/ai/services/ai.service";
import type { AiProposal, CoverLetterProposal, CvProposal } from "@/features/ai/types/Ai";
import { useCvDesigns } from "@/features/documents/hooks/queries/useCvDesigns";
import type { CvDesign } from "@/features/documents/types/Document";
import { useProfile } from "@/features/profile/hooks/queries/useProfile";
import { useProfileEntries } from "@/features/profile/hooks/queries/useProfileEntries";
import {
  useProfileLanguages,
  useProfileSkills,
} from "@/features/profile/hooks/queries/useProfileSkills";
import { HelpLink } from "@/shared/components/help/HelpLink";

/** Revisar una propuesta de IA y generar el PDF (RF-113, RF-118): el CV adaptado
 * o la carta de presentación, según el tipo de la propuesta. */
export function AiProposalReviewPage() {
  const { t } = useTranslation();
  const { applicationId = "", proposalId = "" } = useParams();
  const application = useApplication(applicationId);
  const proposal = useAiProposal(applicationId, proposalId);
  const profile = useProfile();
  const entries = useProfileEntries();
  const skills = useProfileSkills();
  const languages = useProfileLanguages();
  const designs = useCvDesigns();
  const letter = proposal.data?.kind === "cover_letter";
  const title = t(letter ? "ai.letter.reviewTitle" : "ai.review.title");
  useDocumentTitle(title);

  const queries = [proposal, profile, entries, skills, languages, designs];
  if (application.isLoading || queries.some((query) => query.isLoading)) {
    return <DetailSkeleton />;
  }
  if (!application.data) {
    return (
      <ApplicationLoadError
        error={application.error}
        onRetry={() => application.refetch()}
        retrying={application.isFetching}
      />
    );
  }
  if (queries.some((query) => query.isError)) {
    return (
      <ErrorState
        onRetry={() => queries.forEach((query) => void query.refetch())}
        retrying={queries.some((query) => query.isFetching)}
      />
    );
  }

  const data = proposal.data;
  const source: CvSource | null =
    entries.data && skills.data && languages.data
      ? {
          profile: profile.data ?? null,
          entries: entries.data,
          skills: skills.data,
          languages: languages.data,
        }
      : null;
  const ready = data?.status === "succeeded" && data.proposal && source && designs.data;

  return (
    <div className="grid gap-6">
      <div className="grid gap-2">
        <Link
          to={`/applications/${applicationId}`}
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" aria-hidden />
          {application.data.position_title} · {application.data.company.name}
        </Link>
        <div className="flex items-center gap-1">
          <h1 className="text-2xl font-semibold">{title}</h1>
          <HelpLink page={letter ? "aiCoverLetter" : "aiCv"} />
        </div>
        {data && (
          <p className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <Badge variant="secondary" className="gap-1">
              <Sparkles className="size-3" aria-hidden />
              {t("ai.review.generatedWith", { model: data.model })}
            </Badge>
          </p>
        )}
      </div>

      {data && isInFlight(data) && (
        <p className="flex items-center gap-2 text-sm">
          <Loader2 className="size-4 animate-spin" aria-hidden />
          {t("ai.status.running")}
        </p>
      )}
      {data && !isInFlight(data) && data.status !== "succeeded" && (
        <p className="text-sm text-destructive">
          {t(`ai.errors.${data.error_code ?? "ai_interrupted"}`)}
        </p>
      )}
      {ready && (
        <>
          <p
            role="note"
            className="flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-800 dark:text-amber-300"
          >
            <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden />
            <span>{t(letter ? "ai.letter.warning" : "ai.review.warning")}</span>
          </p>
          {/* Se monta con la propuesta ya cargada: el estado inicial sale de ella,
              sin un efecto que la reinicie mientras se edita. */}
          {letter ? (
            <LetterEditor
              key={data.id}
              application={application.data}
              proposal={data}
              content={data.proposal as CoverLetterProposal}
              source={source}
              designs={designs.data}
            />
          ) : (
            <CvEditor
              key={data.id}
              application={application.data}
              proposal={data}
              content={data.proposal as CvProposal}
              source={source}
              designs={designs.data}
            />
          )}
        </>
      )}
    </div>
  );
}

interface EditorProps<T> {
  application: ApplicationDetail;
  proposal: AiProposal;
  content: T;
  source: CvSource;
  designs: CvDesign[];
}

/** Generar el PDF y volver a la biblioteca, que se refresca sola mientras está
 * pendiente. */
function useGenerate(application: ApplicationDetail, proposal: AiProposal) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const create = useCreateAiDocument(application.id, proposal.id);
  const generate = (input: AiDocumentInput) =>
    create.mutate(input, {
      onSuccess: () => {
        toast.success(t("documents.generate.started"));
        navigate("/documents");
      },
      onError: (error) => toast.error(t(errorMessageKey(error), errorMessageParams(error))),
    });
  return { generate, pending: create.isPending };
}

const usableDesigns = (designs: CvDesign[], proposal: AiProposal) =>
  designs.filter((design) => design.languages.includes(proposal.language));

function CvEditor({ application, proposal, content, source, designs }: EditorProps<CvProposal>) {
  const { t } = useTranslation();
  const { generate, pending } = useGenerate(application, proposal);
  const [state, setState] = useState<ReviewState>(() =>
    reviewFromProposal(content, source.entries, source.skills),
  );
  const problem = reviewProblem(state);
  // Se recalcula con cada cambio de la revisión: el "después" es este CV.
  const match = useMemo(
    () => offerMatch(content.requirements, state, source),
    [content.requirements, state, source],
  );

  return (
    <>
      {problem === "outdated" && (
        <p role="alert" className="text-sm text-destructive">
          {t("ai.review.outdated")}
        </p>
      )}

      {match && <OfferMatchCard match={match} source={source} />}

      <ProposalReview
        state={state}
        onChange={setState}
        profileSummary={source.profile?.summary ?? null}
        // Con requisitos, las carencias ya salen en el encaje con la oferta.
        gaps={match ? null : content.gaps}
      />

      <GenerateDocumentCard
        designs={usableDesigns(designs, proposal)}
        defaultName={`CV ${application.position_title} – ${application.company.name}`}
        showAts
        hint={t("ai.review.generateHint")}
        submitLabel={t("ai.review.submit")}
        problem={
          problem && problem !== "outdated" ? t(`ai.review.problems.${problem}`) : null
        }
        pending={pending}
        onGenerate={(design, name) =>
          generate({ design, name, proposal: toReviewedProposal(state) })
        }
      />
    </>
  );
}

function LetterEditor({
  application,
  proposal,
  content,
  source,
  designs,
}: EditorProps<CoverLetterProposal>) {
  const { t } = useTranslation();
  const { generate, pending } = useGenerate(application, proposal);
  const [state, setState] = useState<LetterState>(() => letterFromProposal(content));
  const problem = letterProblem(state);

  return (
    <>
      <LetterReview state={state} onChange={setState} source={source} />

      <GenerateDocumentCard
        designs={usableDesigns(designs, proposal)}
        defaultName={`${t("ai.letter.defaultName")} ${application.position_title} – ${application.company.name}`}
        showAts={false}
        hint={t("ai.letter.generateHint")}
        submitLabel={t("ai.letter.submit")}
        problem={problem ? t(`ai.letter.problems.${problem}`) : null}
        pending={pending}
        onGenerate={(design, name) => generate({ design, name, letter: toReviewedLetter(state) })}
      />
    </>
  );
}
