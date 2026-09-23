import { useState } from "react";
import { Check, Plus, X } from "lucide-react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { errorMessageKey } from "@/shared/lib/errors";
import { formatDateTime } from "@/shared/lib/format";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { useReminders } from "../hooks/queries/useReminders";
import { useCompleteReminder } from "../hooks/mutations/useCompleteReminder";
import { useDismissReminder } from "../hooks/mutations/useDismissReminder";
import { ReminderFormDialog } from "./ReminderFormDialog";

export function RemindersSection({ applicationId }: { applicationId: string }) {
  const { t, i18n } = useTranslation();
  const { data, isLoading } = useReminders({
    page: 1,
    limit: 50,
    application_id: applicationId,
    status: "pending",
    sort_by: "due_at",
    order: "asc",
  });
  const complete = useCompleteReminder();
  const dismiss = useDismissReminder();
  const [formOpen, setFormOpen] = useState(false);

  const onError = (error: Error) => toast.error(t(errorMessageKey(error)));

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">{t("reminders.title")}</h2>
        <Button variant="outline" size="sm" onClick={() => setFormOpen(true)}>
          <Plus />
          {t("reminders.new")}
        </Button>
      </div>

      {isLoading && <p className="text-muted-foreground">{t("common.loading")}</p>}
      {data && data.items.length === 0 && (
        <p className="text-muted-foreground">{t("reminders.empty")}</p>
      )}
      {data && data.items.length > 0 && (
        <ul className="grid gap-2">
          {data.items.map((reminder) => {
            const overdue = new Date(reminder.due_at) < new Date();
            return (
              <li
                key={reminder.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border p-3"
              >
                <div className="grid gap-1">
                  <span className="font-medium">{reminder.title}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">
                      {formatDateTime(reminder.due_at, i18n.language)}
                    </span>
                    {overdue && (
                      <Badge variant="destructive">{t("reminders.overdue")}</Badge>
                    )}
                  </div>
                </div>
                <div className="flex gap-1">
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    aria-label={t("reminders.complete")}
                    onClick={() => complete.mutate(reminder.id, { onError })}
                  >
                    <Check />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    aria-label={t("reminders.dismiss")}
                    onClick={() => dismiss.mutate(reminder.id, { onError })}
                  >
                    <X />
                  </Button>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <ReminderFormDialog
        applicationId={applicationId}
        open={formOpen}
        onOpenChange={setFormOpen}
      />
    </div>
  );
}
