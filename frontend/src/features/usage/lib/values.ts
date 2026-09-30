import { formatBytes } from "@/shared/lib/format";
import type { LimitUsage } from "../types/Usage";

/**
 * Valores para interpolar en los textos de un límite. Con elementos van como
 * números (i18next los formatea y `count` elige singular o plural); con bytes, ya
 * formateados ("99,5 MB") y sin `count`: sus textos no tienen plural.
 */
export function usageValues(item: LimitUsage, locale: string): Record<string, unknown> {
  if (item.unit === "bytes") {
    const format = (value: number | null) => (value === null ? null : formatBytes(value, locale));
    return { used: format(item.used), limit: format(item.limit), remaining: format(item.remaining) };
  }
  return { used: item.used, limit: item.limit, remaining: item.remaining, count: item.remaining };
}
