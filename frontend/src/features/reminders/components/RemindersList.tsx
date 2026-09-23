import { Check, X } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { toast } from "sonner";

import { errorMessageKey } from "@/shared/lib/errors";
import { formatDateTime } from "@/shared/lib/format";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { useCompleteReminder } from "../hooks/mutations/useCompleteReminder";
import { useDismissReminder } from "../hooks/mutations/useDismissReminder";
import type { Reminder } from "../types/Reminder";

interface RemindersListProps {
  reminders: Reminder[];
  /** Falso en el detalle de una solicitud (F4): todos son suyos, sobra repetirlo. */
  showApplication?: boolean;
}

export function RemindersList({ reminders, showApplication = true }: RemindersListProps) {
  const { t, i18n } = useTranslation();
  const complete = useCompleteReminder();
  const dismiss = useDismissReminder();

  const onError = (error: Error) => toast.error(t(errorMessageKey(error)));

  return (
    <ul className="grid gap-2">
      {reminders.map((reminder) => {
        const overdue = reminder.status === "pending" && new Date(reminder.due_at) < new Date();
        return (
          <li
            key={reminder.id}
            className="flex flex-wrap items-center justify-between gap-2 rounded-lg border p-3"
          >
            <div className="grid gap-1">
              <span className="font-medium">{reminder.title}</span>
              <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                <span>{formatDateTime(reminder.due_at, i18n.language)}</span>
                {overdue && <Badge variant="destructive">{t("reminders.overdue")}</Badge>}
                {showApplication &&
                  (reminder.application ? (
                    <Link
                      to={`/applications/${reminder.application.id}`}
                      className="underline underline-offset-2 hover:text-foreground"
                    >
                      {reminder.application.position_title}
                    </Link>
                  ) : (
                    <span>{t("reminders.noApplication")}</span>
                  ))}
              </div>
            </div>
            {reminder.status === "pending" && (
              <div className="flex gap-1">
                <Button
                  variant="ghost"
                  size="icon-sm"
                  className="hover:bg-success/10 hover:text-success-text"
                  aria-label={t("reminders.complete")}
                  onClick={() => complete.mutate(reminder.id, { onError })}
                >
                  <Check />
                </Button>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  className="hover:bg-destructive/10 hover:text-destructive"
                  aria-label={t("reminders.dismiss")}
                  onClick={() => dismiss.mutate(reminder.id, { onError })}
                >
                  <X />
                </Button>
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
