import { useState } from "react";
import { AlertTriangle, ArrowLeft, Loader2, Sparkles } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";

import { useDocumentTitle } from "@/shared/hooks/useDocumentTitle";
import { errorMessageKey, errorMessageParams } from "@/shared/lib/errors";
import { cn } from "@/shared/lib/utils";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { DetailSkeleton } from "@/shared/components/common/Skeletons";
import { ErrorState } from "@/shared/components/common/ErrorState";
import { ApplicationLoadError } from "@/features/applications/components/ApplicationLoadError";
import { useApplication } from "@/features/applications/hooks/queries/useApplication";
import type { ApplicationDetail } from "@/features/applications/types/Application";
import { ProposalReview } from "@/features/ai/components/ProposalReview";
import { useCreateTailoredCv } from "@/features/ai/hooks/mutations/useCreateTailoredCv";
import { useAiProposal } from "@/features/ai/hooks/queries/useAiProposal";
import { isInFlight } from "@/features/ai/hooks/queries/useAiProposals";
import {
  reviewFromProposal,
  reviewProblem,
  toReviewedProposal,
  type ReviewState,
} from "@/features/ai/lib/review";
import type { AiProposal, CvProposal } from "@/features/ai/types/Ai";
import { useCvDesigns } from "@/features/documents/hooks/queries/useCvDesigns";
import { designName, uiCvLanguage } from "@/features/documents/lib/designName";
import type { CvDesign } from "@/features/documents/types/Document";
import { useProfile } from "@/features/profile/hooks/queries/useProfile";
import { useProfileEntries } from "@/features/profile/hooks/queries/useProfileEntries";
import { useProfileSkills } from "@/features/profile/hooks/queries/useProfileSkills";
import type { ProfileEntry } from "@/features/profile/types/ProfileEntry";
import type { ProfileSkill } from "@/features/profile/types/ProfileSkill";

/** Revisar una propuesta de CV adaptado y generar el PDF (RF-113, RF-118). */
export function AiProposalReviewPage() {
  const { t } = useTranslation();
  const { applicationId = "", proposalId = "" } = useParams();
  useDocumentTitle(t("ai.review.title"));
  const application = useApplication(applicationId);
  const proposal = useAiProposal(applicationId, proposalId);
  const profile = useProfile();
  const entries = useProfileEntries();
  const skills = useProfileSkills();
  const designs = useCvDesigns();

  const queries = [proposal, profile, entries, skills, designs];
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
        <h1 className="text-2xl font-semibold">{t("ai.review.title")}</h1>
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
      {data?.status === "succeeded" && data.proposal && entries.data && skills.data && designs.data && (
        // Se monta con la propuesta ya cargada: el estado inicial sale de ella, sin
        // un efecto que la reinicie mientras se edita.
        <ReviewEditor
          key={data.id}
          application={application.data}
          proposal={data}
          content={data.proposal}
          entries={entries.data}
          skills={skills.data}
          profileSummary={profile.data?.summary ?? null}
          designs={designs.data}
        />
      )}
    </div>
  );
}

interface ReviewEditorProps {
  application: ApplicationDetail;
  proposal: AiProposal;
  content: CvProposal;
  entries: ProfileEntry[];
  skills: ProfileSkill[];
  profileSummary: string | null;
  designs: CvDesign[];
}

function ReviewEditor({
  application,
  proposal,
  content,
  entries,
  skills,
  profileSummary,
  designs,
}: ReviewEditorProps) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const create = useCreateTailoredCv(application.id, proposal.id);
  const [state, setState] = useState<ReviewState>(() =>
    reviewFromProposal(content, entries, skills),
  );
  const usable = designs.filter((design) => design.languages.includes(proposal.language));
  const [design, setDesign] = useState(
    (usable.find((item) => item.ats_friendly) ?? usable[0])?.key ?? "",
  );
  const [name, setName] = useState(
    `CV ${application.position_title} – ${application.company.name}`,
  );
  const problem = reviewProblem(state);
  const chosen = usable.find((item) => item.key === design);
  const uiLanguage = uiCvLanguage(i18n.language);

  const generate = () =>
    create.mutate(
      { design, name: name.trim() || null, proposal: toReviewedProposal(state) },
      {
        onSuccess: () => {
          toast.success(t("documents.generate.started"));
          navigate("/documents");
        },
        onError: (error) => toast.error(t(errorMessageKey(error), errorMessageParams(error))),
      },
    );

  return (
    <>
      <p
        role="note"
        className="flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-800 dark:text-amber-300"
      >
        <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden />
        <span>{t("ai.review.warning")}</span>
      </p>
      {problem === "outdated" && (
        <p role="alert" className="text-sm text-destructive">
          {t("ai.review.outdated")}
        </p>
      )}

      <ProposalReview
        state={state}
        onChange={setState}
        profileSummary={profileSummary}
        gaps={content.gaps}
      />

      <Card>
        <CardHeader>
          <CardTitle>{t("ai.review.generate")}</CardTitle>
          <CardDescription>{t("ai.review.generateHint")}</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          <fieldset className="grid gap-2">
            <legend className="mb-2 text-sm font-medium">{t("documents.generate.design")}</legend>
            <div className="grid gap-2 sm:grid-cols-2">
              {usable.map((item) => (
                <label
                  key={item.key}
                  className={cn(
                    "grid cursor-pointer gap-1 rounded-lg border p-3 text-sm transition-colors has-[:focus-visible]:ring-3 has-[:focus-visible]:ring-ring/50",
                    design === item.key ? "border-primary bg-primary/5" : "hover:bg-muted/50",
                  )}
                >
                  <span className="flex items-center justify-between gap-2">
                    <span className="flex items-center gap-2 font-medium">
                      <input
                        type="radio"
                        name="design"
                        value={item.key}
                        checked={design === item.key}
                        onChange={() => setDesign(item.key)}
                        className="accent-primary"
                      />
                      {designName(item, item.key, uiLanguage)}
                    </span>
                    <Badge variant={item.ats_friendly ? "success" : "outline"}>
                      {t(item.ats_friendly ? "documents.generate.ats" : "documents.generate.notAts")}
                    </Badge>
                  </span>
                </label>
              ))}
            </div>
          </fieldset>
          {chosen && !chosen.ats_friendly && (
            <p className="text-sm text-amber-800 dark:text-amber-300">
              {t("documents.generate.notAtsWarning")}
            </p>
          )}
          <div className="grid gap-2 sm:max-w-md">
            <Label htmlFor="tailored-name">{t("documents.fields.name")}</Label>
            <Input
              id="tailored-name"
              value={name}
              maxLength={200}
              onChange={(event) => setName(event.target.value)}
            />
          </div>
          {problem && problem !== "outdated" && (
            <p className="text-sm text-destructive">{t(`ai.review.problems.${problem}`)}</p>
          )}
          <div>
            <Button onClick={generate} disabled={!!problem || !design || create.isPending}>
              {create.isPending && <Loader2 className="animate-spin" />}
              {t("ai.review.submit")}
            </Button>
          </div>
        </CardContent>
      </Card>
    </>
  );
}
