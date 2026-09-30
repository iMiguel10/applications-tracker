import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { errorMessageKey, errorMessageParams } from "@/shared/lib/errors";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { Switch } from "@/shared/components/ui/switch";
import type { Preferences } from "@/features/auth/types/Auth";
import { useEmailVerified } from "@/features/auth/hooks/queries/useEmailVerified";
import { useMeta } from "@/features/meta/hooks/queries/useMeta";
import { useUpdateNotificationSettings } from "../hooks/mutations/useUpdateNotificationSettings";
import {
  NOTICE_FIELDS,
  NOTICE_HOURS,
  NOTIFICATION_TOGGLES,
  type NotificationSettings,
} from "../types/NotificationSettings";
import { NoticeSelect } from "./NoticeSelect";

/** Avisos por email (RF-84): cada tipo se activa por separado y se guarda al
 * momento. Sin correo en la instalación, se explica y no se puede tocar. */
export function NotificationSettingsCard({ preferences }: { preferences: Preferences }) {
  const { t } = useTranslation();
  const { data: meta } = useMeta();
  const { data: verified } = useEmailVerified();
  const update = useUpdateNotificationSettings();
  const unavailable = meta?.email_enabled === false;

  const save = (changes: Partial<NotificationSettings>) =>
    update.mutate(changes, {
      onError: (error) => toast.error(t(errorMessageKey(error), errorMessageParams(error))),
    });

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("notifications.title")}</CardTitle>
        <CardDescription>
          {unavailable
            ? t("notifications.unavailable")
            : verified === false
              ? t("notifications.unverified")
              : t("notifications.description")}
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-5">
        {NOTIFICATION_TOGGLES.map((toggle) => {
          const noticeField =
            toggle in NOTICE_FIELDS ? NOTICE_FIELDS[toggle as keyof typeof NOTICE_FIELDS] : null;
          return (
            <div key={toggle} className="grid gap-3">
              <label className="flex cursor-pointer items-start justify-between gap-4">
                <span className="grid gap-0.5">
                  <span className="text-sm font-medium">{t(`notifications.${toggle}.label`)}</span>
                  <span className="text-sm text-muted-foreground">
                    {t(`notifications.${toggle}.description`)}
                  </span>
                </span>
                <Switch
                  className="mt-0.5"
                  checked={preferences[toggle]}
                  disabled={unavailable}
                  onCheckedChange={(checked) => save({ [toggle]: checked })}
                />
              </label>
              {noticeField && preferences[toggle] && (
                <NoticeSelect
                  value={preferences[noticeField]}
                  options={NOTICE_HOURS[noticeField]}
                  disabled={unavailable}
                  onChange={(hours) => save({ [noticeField]: hours })}
                />
              )}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
