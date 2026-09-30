import type { TFunction } from "i18next";

/** "Al vencer", "2 horas antes", "1 día antes": los múltiplos de 24 se dicen en días. */
export function noticeHoursLabel(hours: number, t: TFunction): string {
  if (hours === 0) return t("notifications.atDue");
  return hours % 24 === 0
    ? t("notifications.noticeDays", { count: hours / 24 })
    : t("notifications.noticeHours", { count: hours });
}
