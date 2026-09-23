import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { useForceLightTheme } from "@/app/providers/useForceLightTheme";

// El mismo recorrido que ya cuenta la app (RF-30…), no una ilustración genérica:
// la vitrina de un cuaderno de bitácora de búsqueda de empleo es su propio progreso.
// Misma familia de color que las insignias de estado reales (ApplicationStatusBadge),
// tomada de los mismos tokens: aquí no hace falta la variante "legible sobre blanco".
const PIPELINE = [
  { status: "applied", color: "var(--color-status-applied)" },
  { status: "interviewing", color: "var(--color-status-interviewing)" },
  { status: "offer", color: "var(--color-success)" },
  { status: "accepted", color: "var(--color-success)" },
] as const;

function StatusPipelinePreview() {
  const { t } = useTranslation();

  return (
    <div className="flex items-center">
      {PIPELINE.map((step, index) => (
        <div key={step.status} className="flex items-center">
          {index > 0 && <div className="h-px w-6 bg-brand-foreground/40" />}
          <div className="flex flex-col items-center gap-2">
            <span
              className="size-2.5 rounded-full"
              style={{ backgroundColor: step.color }}
              aria-hidden
            />
            <span className="whitespace-nowrap text-xs text-brand-foreground/70">
              {t(`applications.status.${step.status}`)}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

interface AuthLayoutProps {
  title: string;
  children: ReactNode;
  footer: ReactNode;
}

/** Marco compartido de login y registro: panel de marca en escritorio, cabecera
 * compacta en móvil. Siempre en claro (F8.4): el panel de marca es oscuro fijo y el
 * formulario está pensado para leerse junto a él, así que el tema del usuario no se
 * aplica aquí (`useForceLightTheme`) — de lo contrario los dos paneles se funden en
 * modo oscuro y el contraste que sostiene el diseño desaparece. */
export function AuthLayout({ title, children, footer }: AuthLayoutProps) {
  const { t } = useTranslation();
  useForceLightTheme();

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="hidden flex-col bg-brand p-10 text-brand-foreground lg:flex">
        <span className="flex items-center gap-2 font-semibold">
          <img src="/brand/logo.png" alt="" className="size-7" />
          {t("app.name")}
        </span>
        <div className="flex flex-1 flex-col justify-center">
          <div className="max-w-sm space-y-10">
            <p className="text-2xl leading-snug font-medium">{t("app.tagline")}</p>
            <StatusPipelinePreview />
          </div>
        </div>
      </div>

      <div className="flex flex-col justify-center px-6 py-12 sm:px-12 lg:px-16">
        <span className="mb-10 flex items-center gap-2 font-semibold lg:hidden">
          <img src="/brand/logo.png" alt="" className="size-7" />
          {t("app.name")}
        </span>

        <div className="mx-auto w-full max-w-sm">
          <h1 className="text-2xl font-semibold">{title}</h1>
          <div className="mt-6">{children}</div>
          <div className="mt-6">{footer}</div>
        </div>
      </div>
    </div>
  );
}
