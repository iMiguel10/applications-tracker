import type { LucideIcon } from "lucide-react";

import { cn } from "@/shared/lib/utils";

export interface ViewOption<T extends string> {
  value: T;
  label: string;
  icon: LucideIcon;
}

interface ViewToggleProps<T extends string> {
  /** Nombre del grupo para lectores de pantalla ("Vista"). */
  label: string;
  options: ViewOption<T>[];
  value: T;
  onChange: (value: T) => void;
}

/**
 * Selector de vista (Lista/Tablero, Mes/Semana). La opción activa va en el color
 * primario para que se vea a la primera cuál es la vista actual, y cada botón
 * dice si está pulsado con `aria-pressed`. Colócalo donde no cambie de sitio al
 * cambiar de vista (junto al título).
 */
export function ViewToggle<T extends string>({
  label,
  options,
  value,
  onChange,
}: ViewToggleProps<T>) {
  return (
    <div
      role="group"
      aria-label={label}
      className="inline-flex rounded-lg border bg-card p-0.5 shadow-xs"
    >
      {options.map(({ value: option, label: optionLabel, icon: Icon }) => {
        const active = option === value;
        return (
          <button
            key={option}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(option)}
            className={cn(
              "inline-flex h-7 items-center gap-1.5 rounded-md px-2.5 text-sm font-medium transition-colors focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none [&_svg]:size-4",
              active
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            <Icon aria-hidden />
            {optionLabel}
          </button>
        );
      })}
    </div>
  );
}
