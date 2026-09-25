import { useState, type ReactNode } from "react";
import {
  Archive,
  ArchiveRestore,
  ExternalLink,
  Pencil,
  RefreshCw,
  Trash2,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";

import { useDocumentTitle } from "@/shared/hooks/useDocumentTitle";
import { errorMessageKey, errorMessageParams } from "@/shared/lib/errors";
import { formatDateOnly, formatDateTime, formatSalaryRange } from "@/shared/lib/format";
import { Button, buttonVariants } from "@/shared/components/ui/button";
import { Card, CardContent } from "@/shared/components/ui/card";
import { DetailSkeleton } from "@/shared/components/common/Skeletons";
import { ApplicationLoadError } from "@/features/applications/components/ApplicationLoadError";
import { ApplicationStatusBadge } from "@/features/applications/components/ApplicationStatusBadge";
import { ChangeStatusDialog } from "@/features/applications/components/ChangeStatusDialog";
import { DeleteApplicationDialog } from "@/features/applications/components/DeleteApplicationDialog";
import { StatusHistoryTimeline } from "@/features/applications/components/StatusHistoryTimeline";
import { useApplication } from "@/features/applications/hooks/queries/useApplication";
import { useSetArchived } from "@/features/applications/hooks/mutations/useSetArchived";
import { InterviewsSection } from "@/features/interviews/components/InterviewsSection";
import { RemindersSection } from "@/features/reminders/components/RemindersSection";

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid gap-1">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd>{children ?? "—"}</dd>
    </div>
  );
}

export function ApplicationDetailPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { applicationId = "" } = useParams();
  const { data: application, isLoading, error, isFetching, refetch } =
    useApplication(applicationId);
  useDocumentTitle(application?.position_title);
  const setArchived = useSetArchived();
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [changeStatusOpen, setChangeStatusOpen] = useState(false);

  if (isLoading) return <DetailSkeleton />;
  if (!application) {
    return (
      <ApplicationLoadError error={error} onRetry={() => refetch()} retrying={isFetching} />
    );
  }

  const archived = !!application.archived_at;
  const lang = i18n.language;

  const toggleArchived = () =>
    setArchived.mutate(
      { id: application.id, archived: !archived },
      {
        onSuccess: () =>
          toast.success(t(archived ? "applications.unarchivedToast" : "applications.archivedToast")),
        onError: (error) => toast.error(t(errorMessageKey(error), errorMessageParams(error))),
      },
    );

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="grid gap-1">
          <p className="text-sm text-muted-foreground">{application.company.name}</p>
          <h1 className="text-2xl font-semibold">{application.position_title}</h1>
          <div className="flex items-center gap-2">
            <ApplicationStatusBadge status={application.status} />
            {archived && (
              <span className="text-sm text-muted-foreground">{t("applications.archived")}</span>
            )}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {application.allowed_transitions.length > 0 && (
            <Button variant="outline" onClick={() => setChangeStatusOpen(true)}>
              <RefreshCw />
              {t("applications.changeStatus")}
            </Button>
          )}
          <Link
            to={`/applications/${application.id}/edit`}
            className={buttonVariants({ variant: "outline" })}
          >
            <Pencil />
            {t("common.edit")}
          </Link>
          <Button variant="outline" onClick={toggleArchived} disabled={setArchived.isPending}>
            {archived ? <ArchiveRestore /> : <Archive />}
            {t(archived ? "applications.unarchive" : "applications.archive")}
          </Button>
          <Button variant="outline" onClick={() => setDeleteOpen(true)}>
            <Trash2 />
            {t("common.delete")}
          </Button>
        </div>
      </div>

      {/* Escritorio: los datos a la izquierda; lo que cambia con el tiempo (historial,
          entrevistas, recordatorios) en una columna a la derecha. */}
      <div className="grid items-start gap-6 lg:grid-cols-[3fr_2fr]">
        <Card>
          <CardContent>
            <dl className="grid gap-4 sm:grid-cols-2">
              <Field label={t("applications.fields.appliedAt")}>
                {formatDateOnly(application.applied_at, lang)}
              </Field>
              <Field label={t("applications.fields.location")}>{application.location}</Field>
              <Field label={t("applications.fields.workMode")}>
                {application.work_mode && t(`applications.workMode.${application.work_mode}`)}
              </Field>
              <Field label={t("applications.fields.source")}>
                {application.source && t(`applications.source.${application.source}`)}
              </Field>
              <Field label={t("applications.fields.salary")}>
                {formatSalaryRange(
                  application.salary_min,
                  application.salary_max,
                  application.salary_currency,
                  lang,
                )}
              </Field>
              <Field label={t("applications.fields.jobUrl")}>
                {application.job_url && (
                  <a
                    href={application.job_url}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="inline-flex items-center gap-1 underline underline-offset-2"
                  >
                    {new URL(application.job_url).hostname}
                    <ExternalLink className="size-3.5" />
                  </a>
                )}
              </Field>
            </dl>
            {application.notes && (
              <div className="mt-6 grid gap-1">
                <p className="text-sm text-muted-foreground">{t("common.fields.notes")}</p>
                <p className="whitespace-pre-wrap">{application.notes}</p>
              </div>
            )}
            <p className="mt-6 border-t pt-4 text-xs text-muted-foreground">
              {t("applications.timestamps", {
                created: formatDateTime(application.created_at, lang),
                updated: formatDateTime(application.updated_at, lang),
              })}
            </p>
          </CardContent>
        </Card>

        <div className="grid gap-6">
          <StatusHistoryTimeline applicationId={application.id} />

          <InterviewsSection
            application={application}
            onSuggestInterviewing={() => setChangeStatusOpen(true)}
          />

          <RemindersSection applicationId={application.id} />
        </div>
      </div>

      <ChangeStatusDialog
        application={application}
        open={changeStatusOpen}
        onOpenChange={setChangeStatusOpen}
      />
      <DeleteApplicationDialog
        application={application}
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        onDeleted={() => navigate("/applications", { replace: true })}
      />
    </div>
  );
}
