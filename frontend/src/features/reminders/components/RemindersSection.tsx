import { useState } from "react";
import { BellRing, Plus } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "@/shared/components/ui/button";
import { EmptyState } from "@/shared/components/common/EmptyState";
import { ListSkeleton } from "@/shared/components/common/Skeletons";
import { useReminders } from "../hooks/queries/useReminders";
import { ReminderFormDialog } from "./ReminderFormDialog";
import { RemindersList } from "./RemindersList";

export function RemindersSection({ applicationId }: { applicationId: string }) {
  const { t } = useTranslation();
  const { data, isLoading } = useReminders({
    page: 1,
    limit: 50,
    application_id: applicationId,
    status: "pending",
    sort_by: "due_at",
    order: "asc",
  });
  const [formOpen, setFormOpen] = useState(false);

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">{t("reminders.title")}</h2>
        <Button variant="outline" size="sm" onClick={() => setFormOpen(true)}>
          <Plus />
          {t("reminders.new")}
        </Button>
      </div>

      {isLoading && <ListSkeleton />}
      {data && data.items.length === 0 && (
        <EmptyState size="sm" icon={BellRing} title={t("reminders.empty")} />
      )}
      {data && data.items.length > 0 && (
        <RemindersList reminders={data.items} showApplication={false} />
      )}

      <ReminderFormDialog
        applicationId={applicationId}
        open={formOpen}
        onOpenChange={setFormOpen}
      />
    </div>
  );
}
