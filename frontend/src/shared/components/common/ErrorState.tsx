import { RotateCw, TriangleAlert } from "lucide-react";
import { useTranslation } from "react-i18next";

import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/components/ui/button";

interface ErrorStateProps {
  /** Normalmente el `refetch` de la query que ha fallado. */
  onRetry?: () => void;
  retrying?: boolean;
  /** Clave i18n del título; por defecto, "no se ha podido cargar". */
  titleKey?: string;
  className?: string;
}

export function ErrorState({ onRetry, retrying, titleKey, className }: ErrorStateProps) {
  const { t } = useTranslation();

  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-center gap-3 rounded-xl border border-destructive/25 bg-card px-6 py-12 text-center",
        className,
      )}
    >
      <span className="flex size-12 items-center justify-center rounded-full bg-destructive/10 text-destructive">
        <TriangleAlert className="size-5" aria-hidden />
      </span>
      <div className="grid max-w-sm gap-1">
        <p className="font-medium">{t(titleKey ?? "common.loadError.title")}</p>
        <p className="text-sm text-muted-foreground">{t("common.loadError.description")}</p>
      </div>
      {onRetry && (
        <Button variant="outline" className="mt-2" onClick={onRetry} disabled={retrying}>
          <RotateCw className={cn(retrying && "motion-safe:animate-spin")} />
          {t("common.retry")}
        </Button>
      )}
    </div>
  );
}
