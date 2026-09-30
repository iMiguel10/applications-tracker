import { useMemo } from "react";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import { Switch } from "@/shared/components/ui/switch";
import type { Preferences } from "@/features/auth/types/Auth";
import { useEmailVerified } from "@/features/auth/hooks/queries/useEmailVerified";
import { useMeta } from "@/features/meta/hooks/queries/useMeta";
import { useUpdateNotificationSettings } from "../hooks/mutations/useUpdateNotificationSettings";
import { noticeHoursLabel } from "../lib/noticeHours";
import {
  INTERVIEW_NOTICE_HOURS,
  NOTIFICATION_TOGGLES,
  type NotificationSettings,
  type NotificationToggle,
} from "../types/NotificationSettings";

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

  // Un valor fijado por la API que no esté en la lista también se puede ver.
  const hours = useMemo(
    () =>
      [...new Set([...INTERVIEW_NOTICE_HOURS, preferences.interview_notice_hours])]
        .sort((a, b) => a - b)
        .map((value) => ({ value: String(value), label: noticeHoursLabel(value, t) })),
    [preferences.interview_notice_hours, t],
  );

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
        {NOTIFICATION_TOGGLES.map((toggle: NotificationToggle) => (
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
            {toggle === "notify_interview" && preferences.notify_interview && (
              <div className="flex flex-wrap items-center gap-2">
                <span id="interview-notice-label" className="text-sm text-muted-foreground">
                  {t("notifications.noticeLabel")}
                </span>
                <Select
                  items={hours}
                  value={String(preferences.interview_notice_hours)}
                  onValueChange={(value) =>
                    value && save({ interview_notice_hours: Number(value) })
                  }
                  disabled={unavailable}
                >
                  <SelectTrigger className="w-44" aria-labelledby="interview-notice-label">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {hours.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
