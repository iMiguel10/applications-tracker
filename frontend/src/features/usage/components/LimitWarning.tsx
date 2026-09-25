import { AlertTriangle } from "lucide-react";
import { useTranslation } from "react-i18next";

import { cn } from "@/shared/lib/utils";
import { useUsage } from "../hooks/queries/useUsage";
import { usageLevel } from "../lib/level";
import type { LimitKey } from "../types/Usage";

/**
 * Aviso en el sitio donde se gasta un límite (RF-144), p. ej. el formulario de
 * nueva solicitud. No pinta nada por debajo del umbral de aviso: la mayoría de las
 * cuentas no lo verán nunca. Si falla la consulta, tampoco: el backend sigue
 * aplicando el límite y su error lo explica.
 */
export function LimitWarning({ limitKey, className }: { limitKey: LimitKey; className?: string }) {
  const { t } = useTranslation();
  const { data } = useUsage();
  const item = data?.limits.find((limit) => limit.key === limitKey);
  if (!data || !item) return null;

  const level = usageLevel(item, data.warning_ratio);
  if (level === "ok" || level === "unlimited") return null;

  // count elige singular o plural ("te queda 1", "te quedan 3").
  const values = {
    used: item.used,
    limit: item.limit,
    remaining: item.remaining,
    count: item.remaining,
  };
  return (
    <p
      role={level === "reached" ? "alert" : "status"}
      className={cn(
        "flex items-start gap-2 rounded-md border px-3 py-2 text-sm",
        level === "reached"
          ? "border-destructive/30 bg-destructive/5 text-destructive"
          : "border-amber-500/40 bg-amber-500/10 text-amber-800 dark:text-amber-300",
        className,
      )}
    >
      <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden />
      <span>{t(`usage.${level}.${limitKey}`, values)}</span>
    </p>
  );
}
