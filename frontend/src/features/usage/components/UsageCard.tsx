import { useTranslation } from "react-i18next";

import { cn } from "@/shared/lib/utils";
import { ErrorState } from "@/shared/components/common/ErrorState";
import { ListSkeleton } from "@/shared/components/common/Skeletons";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { useUsage } from "../hooks/queries/useUsage";
import { usageLevel, type UsageLevel } from "../lib/level";

const BAR_CLASSES: Record<Exclude<UsageLevel, "unlimited">, string> = {
  ok: "bg-primary",
  warning: "bg-amber-500",
  reached: "bg-destructive",
};

const TEXT_CLASSES: Record<UsageLevel, string> = {
  unlimited: "text-muted-foreground",
  ok: "text-muted-foreground",
  warning: "text-amber-700 dark:text-amber-400",
  reached: "text-destructive",
};

/** Consumo de cada límite de la cuenta (RF-141): lo usado, el límite y lo que
 * queda, con una barra que cambia de color al pasar del aviso (RF-144). */
export function UsageCard() {
  const { t } = useTranslation();
  const { data, isLoading, isError, isFetching, refetch } = useUsage();

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("usage.title")}</CardTitle>
        <CardDescription>{t("usage.description")}</CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading && <ListSkeleton rows={3} />}
        {isError && <ErrorState onRetry={() => refetch()} retrying={isFetching} />}
        {data && (
          <ul className="grid gap-4">
            {data.limits.map((item) => {
              const level = usageLevel(item, data.warning_ratio);
              const label = t(`usage.limits.${item.key}`);
              if (level === "unlimited" || item.limit === null) {
                // Sin barra: no hay tope con el que comparar.
                return (
                  <li key={item.key} className="flex flex-wrap items-baseline justify-between gap-x-3 text-sm">
                    <span className="font-medium">{label}</span>
                    <span className={cn("tabular-nums", TEXT_CLASSES.unlimited)}>
                      {t("usage.amountsUnlimited", { used: item.used })}
                    </span>
                  </li>
                );
              }
              const percent = item.limit > 0 ? Math.min(100, (item.used / item.limit) * 100) : 100;
              return (
                <li key={item.key} className="grid gap-1.5">
                  <div className="flex flex-wrap items-baseline justify-between gap-x-3 text-sm">
                    <span className="font-medium">{label}</span>
                    <span className={cn("tabular-nums", TEXT_CLASSES[level])}>
                      {t("usage.amounts", {
                        used: item.used,
                        limit: item.limit,
                        remaining: item.remaining,
                        count: item.remaining,
                      })}
                    </span>
                  </div>
                  <div
                    role="progressbar"
                    aria-label={label}
                    aria-valuemin={0}
                    aria-valuemax={item.limit}
                    aria-valuenow={Math.min(item.used, item.limit)}
                    className="h-2 overflow-hidden rounded-full bg-muted"
                  >
                    <div
                      className={cn("h-full rounded-full", BAR_CLASSES[level])}
                      style={{ width: `${percent}%` }}
                    />
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
