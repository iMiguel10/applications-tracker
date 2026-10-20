import { useState } from "react";
import { Undo2 } from "lucide-react";
import { useTranslation } from "react-i18next";

import { formatDateTime } from "@/shared/lib/format";
import { useAccountZone } from "@/features/auth/hooks/useAccountZone";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent } from "@/shared/components/ui/card";
import { ListSkeleton } from "@/shared/components/common/Skeletons";
import { ApplicationStatusBadge } from "./ApplicationStatusBadge";
import { UndoStatusChangeDialog } from "./UndoStatusChangeDialog";
import { useApplicationStatusChanges } from "../hooks/queries/useApplicationStatusChanges";
import { HelpLink } from "@/shared/components/help/HelpLink";

export function StatusHistoryTimeline({ applicationId }: { applicationId: string }) {
  const { t, i18n } = useTranslation();
  const zone = useAccountZone();
  const { data: history, isLoading } = useApplicationStatusChanges(applicationId);
  const [undoOpen, setUndoOpen] = useState(false);

  if (isLoading) return <ListSkeleton rows={1} />;
  if (!history || history.length === 0) return null;

  // El cambio inicial (from_status null) no se puede deshacer: invariante 4.
  const canUndo = history.length > 1;

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1">
          <h2 className="font-semibold">{t("applications.history")}</h2>
          <HelpLink page="statusChanges" />
        </div>
        {canUndo && (
          <Button variant="ghost" size="sm" onClick={() => setUndoOpen(true)}>
            <Undo2 />
            {t("applications.undoLast")}
          </Button>
        )}
      </div>

      <Card size="sm">
        <CardContent>
          <ol className="grid gap-3 border-l pl-4">
            {history.map((change) => (
              <li key={change.id} className="grid gap-1">
                <div className="flex flex-wrap items-center gap-2">
                  <ApplicationStatusBadge status={change.to_status} />
                  <span className="text-sm text-muted-foreground">
                    {formatDateTime(change.changed_at, i18n.language, zone)}
                  </span>
                </div>
                {change.note && <p className="text-sm whitespace-pre-wrap">{change.note}</p>}
              </li>
            ))}
          </ol>
        </CardContent>
      </Card>

      <UndoStatusChangeDialog
        applicationId={applicationId}
        open={undoOpen}
        onOpenChange={setUndoOpen}
      />
    </div>
  );
}
