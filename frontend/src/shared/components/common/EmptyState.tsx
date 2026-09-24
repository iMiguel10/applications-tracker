import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/shared/lib/utils";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  /** Lo siguiente que puede hacer el usuario: un vacío es una invitación a actuar. */
  action?: ReactNode;
  /** `sm` para secciones dentro de una página (entrevistas, recordatorios…). */
  size?: "default" | "sm";
  className?: string;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  size = "default",
  className,
}: EmptyStateProps) {
  const small = size === "sm";

  return (
    <div
      className={cn(
        "flex flex-col items-center rounded-xl border border-dashed bg-card text-center",
        small ? "gap-2 px-4 py-6" : "gap-3 px-6 py-14",
        className,
      )}
    >
      <span
        className={cn(
          "flex items-center justify-center rounded-full bg-accent text-accent-foreground",
          small ? "size-9" : "size-12",
        )}
      >
        <Icon className={small ? "size-4" : "size-5"} aria-hidden />
      </span>
      <div className="grid max-w-sm gap-1">
        <p className={cn("font-medium", small ? "text-sm" : "text-base")}>{title}</p>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
      {action && <div className={small ? "mt-1" : "mt-2"}>{action}</div>}
    </div>
  );
}
