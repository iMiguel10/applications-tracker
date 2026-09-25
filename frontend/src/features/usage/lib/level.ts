import type { LimitUsage } from "../types/Usage";

export type UsageLevel = "unlimited" | "ok" | "warning" | "reached";

/** "reached" al no quedar nada; "warning" desde `warningRatio` (RF-144). */
export function usageLevel(item: LimitUsage, warningRatio: number): UsageLevel {
  if (item.limit === null || item.remaining === null) return "unlimited";
  if (item.remaining <= 0) return "reached";
  if (item.limit > 0 && item.used / item.limit >= warningRatio) return "warning";
  return "ok";
}
