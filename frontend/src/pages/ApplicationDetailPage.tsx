import { useState, type ReactNode } from "react";
import { Archive, ArchiveRestore, ExternalLink, Pencil, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";

import { errorMessageKey } from "@/shared/lib/errors";
import { formatDateOnly, formatDateTime, formatSalaryRange } from "@/shared/lib/format";
import { Button, buttonVariants } from "@/shared/components/ui/button";
import { Card, CardContent } from "@/shared/components/ui/card";
import { ApplicationStatusBadge } from "@/features/applications/components/ApplicationStatusBadge";
import { DeleteApplicationDialog } from "@/features/applications/components/DeleteApplicationDialog";
import { useApplication } from "@/features/applications/hooks/queries/useApplication";
import { useSetArchived } from "@/features/applications/hooks/mutations/useSetArchived";

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
  const { data: application, isLoading, isError } = useApplication(applicationId);
  const setArchived = useSetArchived();
  const [deleteOpen, setDeleteOpen] = useState(false);

  if (isLoading) return <p className="text-muted-foreground">{t("common.loading")}</p>;
  if (isError || !application) return <p className="text-destructive">{t("errors.not_found")}</p>;

  const archived = !!application.archived_at;
  const lang = i18n.language;

  const toggleArchived = () =>
    setArchived.mutate(
      { id: application.id, archived: !archived },
      {
        onSuccess: () =>
          toast.success(t(archived ? "applications.unarchivedToast" : "applications.archivedToast")),
        onError: (error) => toast.error(t(errorMessageKey(error))),
      },
    );

  return (
    <div className="grid max-w-3xl gap-6">
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
        </CardContent>
      </Card>

      <p className="text-sm text-muted-foreground">
        {t("applications.timestamps", {
          created: formatDateTime(application.created_at, lang),
          updated: formatDateTime(application.updated_at, lang),
        })}
      </p>

      <DeleteApplicationDialog
        application={application}
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        onDeleted={() => navigate("/applications", { replace: true })}
      />
    </div>
  );
}
