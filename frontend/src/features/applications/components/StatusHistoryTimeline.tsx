import { useState } from "react";
import { Undo2 } from "lucide-react";
import { useTranslation } from "react-i18next";

import { formatDateTime } from "@/shared/lib/format";
import { Button } from "@/shared/components/ui/button";
import { ApplicationStatusBadge } from "./ApplicationStatusBadge";
import { UndoStatusChangeDialog } from "./UndoStatusChangeDialog";
import { useApplicationStatusChanges } from "../hooks/queries/useApplicationStatusChanges";

export function StatusHistoryTimeline({ applicationId }: { applicationId: string }) {
  const { t, i18n } = useTranslation();
  const { data: history, isLoading } = useApplicationStatusChanges(applicationId);
  const [undoOpen, setUndoOpen] = useState(false);

  if (isLoading) return <p className="text-muted-foreground">{t("common.loading")}</p>;
  if (!history || history.length === 0) return null;

  // El cambio inicial (from_status null) no se puede deshacer: invariante 4.
  const canUndo = history.length > 1;

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">{t("applications.history")}</h2>
        {canUndo && (
          <Button variant="ghost" size="sm" onClick={() => setUndoOpen(true)}>
            <Undo2 />
            {t("applications.undoLast")}
          </Button>
        )}
      </div>

      <ol className="grid gap-3 border-l pl-4">
        {history.map((change) => (
          <li key={change.id} className="grid gap-1">
            <div className="flex flex-wrap items-center gap-2">
              <ApplicationStatusBadge status={change.to_status} />
              <span className="text-sm text-muted-foreground">
                {formatDateTime(change.changed_at, i18n.language)}
              </span>
            </div>
            {change.note && <p className="text-sm whitespace-pre-wrap">{change.note}</p>}
          </li>
        ))}
      </ol>

      <UndoStatusChangeDialog
        applicationId={applicationId}
        open={undoOpen}
        onOpenChange={setUndoOpen}
      />
    </div>
  );
}
