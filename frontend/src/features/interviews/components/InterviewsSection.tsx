import { useState } from "react";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import type { Application } from "@/features/applications/types/Application";
import { formatDateTime } from "@/shared/lib/format";
import { Button } from "@/shared/components/ui/button";
import { useInterviews } from "../hooks/queries/useInterviews";
import { InterviewFormDialog } from "./InterviewFormDialog";
import { DeleteInterviewDialog } from "./DeleteInterviewDialog";
import type { Interview } from "../types/Interview";

interface InterviewsSectionProps {
  application: Application;
  /** RF-42: tras programar una entrevista en applied/screening, se propone pasar a
   * interviewing (sin forzarlo). Abre el diálogo de cambio de estado ya existente. */
  onSuggestInterviewing: () => void;
}

export function InterviewsSection({ application, onSuggestInterviewing }: InterviewsSectionProps) {
  const { t, i18n } = useTranslation();
  const { data: interviews, isLoading } = useInterviews(application.id);
  const [formTarget, setFormTarget] = useState<Interview | null | undefined>(undefined);
  const [deleteTarget, setDeleteTarget] = useState<Interview | null>(null);

  const openCreate = () => setFormTarget(null);
  const openEdit = (interview: Interview) => setFormTarget(interview);

  const onCreated = () => {
    if (application.allowed_transitions.includes("interviewing")) {
      toast(t("interviews.suggestInterviewing"), {
        action: {
          label: t("applications.changeStatus"),
          onClick: onSuggestInterviewing,
        },
      });
    }
  };

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">{t("interviews.title")}</h2>
        <Button variant="outline" size="sm" onClick={openCreate}>
          <Plus />
          {t("interviews.new")}
        </Button>
      </div>

      {isLoading && <p className="text-muted-foreground">{t("common.loading")}</p>}
      {interviews && interviews.length === 0 && (
        <p className="text-muted-foreground">{t("interviews.empty")}</p>
      )}
      {interviews && interviews.length > 0 && (
        <ul className="grid gap-2">
          {interviews.map((interview) => (
            <li
              key={interview.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg border bg-card p-3"
            >
              <div className="grid gap-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium">
                    {formatDateTime(interview.scheduled_at, i18n.language)}
                  </span>
                  <span className="text-sm text-muted-foreground">
                    {t(`interviews.outcome.${interview.outcome}`)}
                  </span>
                </div>
                <p className="text-sm text-muted-foreground">
                  {[
                    interview.interview_type && t(`interviews.type.${interview.interview_type}`),
                    interview.format && t(`interviews.format.${interview.format}`),
                    interview.interviewers,
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
              </div>
              <div className="flex gap-1">
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label={t("common.edit")}
                  onClick={() => openEdit(interview)}
                >
                  <Pencil />
                </Button>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label={t("common.delete")}
                  onClick={() => setDeleteTarget(interview)}
                >
                  <Trash2 />
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <InterviewFormDialog
        applicationId={application.id}
        interview={formTarget}
        open={formTarget !== undefined}
        onOpenChange={(open) => !open && setFormTarget(undefined)}
        onCreated={onCreated}
      />
      {deleteTarget && (
        <DeleteInterviewDialog
          applicationId={application.id}
          interviewId={deleteTarget.id}
          open={!!deleteTarget}
          onOpenChange={(open) => !open && setDeleteTarget(null)}
        />
      )}
    </div>
  );
}
