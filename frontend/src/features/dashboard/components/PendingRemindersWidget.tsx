import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { formatDateTime } from "@/shared/lib/format";
import { Badge } from "@/shared/components/ui/badge";
import {
  Card,
  CardAction,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import type { Reminder } from "@/features/reminders/types/Reminder";

interface PendingRemindersWidgetProps {
  reminders: Reminder[];
  total: number;
}

// Solo lectura, con enlace al listado (decisión del usuario, 2026-09-23): completar
// o descartar directamente desde aquí se decide una vez terminado F6.
export function PendingRemindersWidget({ reminders, total }: PendingRemindersWidgetProps) {
  const { t, i18n } = useTranslation();

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("dashboard.pendingReminders.title")}</CardTitle>
        <CardAction>
          <Link
            to="/reminders"
            className="text-sm underline underline-offset-2 hover:text-foreground"
          >
            {t("dashboard.pendingReminders.viewAll")}
          </Link>
        </CardAction>
      </CardHeader>
      <CardContent className="grid gap-3">
        {reminders.length === 0 && (
          <p className="text-muted-foreground">{t("dashboard.pendingReminders.empty")}</p>
        )}
        {reminders.length > 0 && (
          <ul className="grid gap-2">
            {reminders.map((reminder) => {
              const overdue = new Date(reminder.due_at) < new Date();
              return (
                <li key={reminder.id} className="grid gap-0.5">
                  <span className="font-medium">{reminder.title}</span>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <span>{formatDateTime(reminder.due_at, i18n.language)}</span>
                    {overdue && <Badge variant="destructive">{t("reminders.overdue")}</Badge>}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
        {total > reminders.length && (
          <p className="text-sm text-muted-foreground">
            {t("dashboard.pendingReminders.more", { count: total - reminders.length })}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
