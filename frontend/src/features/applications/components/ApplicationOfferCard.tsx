import { useState } from "react";
import { FileText } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { DocumentViewerDialog } from "@/features/documents/components/DocumentViewerDialog";
import type { DocumentRef, DocumentSummary } from "@/features/documents/types/Document";
import type { ApplicationDetail } from "../types/Application";

// Por encima de esto, la descripción se muestra recortada con "Ver completa".
const COLLAPSED_LENGTH = 600;

/** La descripción de la oferta y el CV y la carta enviados (RF-27, RF-28). */
export function ApplicationOfferCard({ application }: { application: ApplicationDetail }) {
  const { t } = useTranslation();
  const [viewing, setViewing] = useState<DocumentRef | null>(null);
  const [expanded, setExpanded] = useState(false);

  const description = application.job_description;
  const long = !!description && description.length > COLLAPSED_LENGTH;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("applications.fields.offerAndDocuments")}</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-6">
        <dl className="grid gap-4 sm:grid-cols-2">
          <SentDocument
            label={t("applications.fields.cvDocument")}
            document={application.cv_document}
            onView={setViewing}
          />
          <SentDocument
            label={t("applications.fields.coverLetterDocument")}
            document={application.cover_letter_document}
            onView={setViewing}
          />
        </dl>

        <div className="grid gap-1">
          <p className="text-sm text-muted-foreground">{t("applications.fields.jobDescription")}</p>
          {description ? (
            <>
              <p className="whitespace-pre-wrap">
                {long && !expanded ? `${description.slice(0, COLLAPSED_LENGTH).trimEnd()}…` : description}
              </p>
              {long && (
                <Button
                  variant="link"
                  className="h-auto justify-self-start p-0"
                  aria-expanded={expanded}
                  onClick={() => setExpanded((value) => !value)}
                >
                  {t(expanded ? "applications.showLess" : "applications.showMore")}
                </Button>
              )}
            </>
          ) : (
            <p className="text-muted-foreground">
              {t("applications.noJobDescription")}{" "}
              <Link
                to={`/applications/${application.id}/edit`}
                className="underline underline-offset-2 hover:text-foreground"
              >
                {t("applications.addJobDescription")}
              </Link>
            </p>
          )}
        </div>
      </CardContent>
      <DocumentViewerDialog document={viewing} onClose={() => setViewing(null)} />
    </Card>
  );
}

function SentDocument({
  label,
  document,
  onView,
}: {
  label: string;
  document: DocumentSummary | null;
  onView: (document: DocumentRef) => void;
}) {
  const { t } = useTranslation();
  return (
    <div className="grid gap-1">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd>
        {document ? (
          <span className="inline-flex min-w-0 items-center gap-2">
            <FileText className="size-4 shrink-0 text-muted-foreground" aria-hidden />
            {document.status === "ready" ? (
              <button
                type="button"
                onClick={() => onView(document)}
                className="truncate text-left underline underline-offset-2 hover:text-foreground"
                title={document.name}
              >
                {document.name}
              </button>
            ) : (
              <span className="truncate">{document.name}</span>
            )}
            {document.archived_at && (
              <span className="text-sm text-muted-foreground">({t("documents.usage.archived")})</span>
            )}
          </span>
        ) : (
          <span className="text-muted-foreground">{t("documents.none")}</span>
        )}
      </dd>
    </div>
  );
}
