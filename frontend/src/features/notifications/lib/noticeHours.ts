import type { TFunction } from "i18next";

/** "2 horas antes", "1 día antes": los múltiplos de 24 se dicen en días. */
export function noticeHoursLabel(hours: number, t: TFunction): string {
  return hours % 24 === 0
    ? t("notifications.noticeDays", { count: hours / 24 })
    : t("notifications.noticeHours", { count: hours });
}
