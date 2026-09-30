import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { useDocumentDetail } from "../hooks/queries/useDocumentDetail";

/** En qué solicitudes se envió un documento (RF-92). Si falla la consulta no pinta
 * nada: el visor sigue sirviendo para ver el PDF. */
export function DocumentUsageList({ documentId }: { documentId: string }) {
  const { t } = useTranslation();
  const { data } = useDocumentDetail(documentId);
  if (!data) return null;

  if (data.used_in.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("documents.usage.none")}</p>;
  }
  return (
    <div className="grid gap-1 text-sm">
      <p className="text-muted-foreground">
        {t("documents.usage.title", { count: data.used_in.length })}
      </p>
      <ul className="flex flex-wrap gap-x-4 gap-y-1">
        {data.used_in.map((usage) => (
          <li key={`${usage.application_id}-${usage.used_as}`}>
            <Link
              to={`/applications/${usage.application_id}`}
              className="underline underline-offset-2 hover:text-foreground"
            >
              {usage.position_title} · {usage.company_name}
            </Link>
            {usage.application_archived && (
              <span className="text-muted-foreground"> ({t("documents.usage.archived")})</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
