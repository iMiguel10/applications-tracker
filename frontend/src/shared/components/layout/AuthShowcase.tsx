import { useState, type CSSProperties } from "react";
import { BellRing } from "lucide-react";
import { useTranslation } from "react-i18next";

import { ApplicationStatusBadge } from "@/features/applications/components/ApplicationStatusBadge";
import type { ApplicationStatus } from "@/features/applications/types/Application";

const DAY_MS = 86_400_000;

// Ilustra el lema con la propia interfaz: la pila son "todas tus candidaturas", el
// historial de la de delante es "su historia" y el recordatorio, "tu próximo paso".
const BACKGROUND_CARDS: { company: string; role: string; status: ApplicationStatus }[] = [
  { company: "Kestrel Data", role: "Data Analyst", status: "applied" },
  { company: "Orbital Studio", role: "Product Designer", status: "screening" },
];

const HISTORY: { status: ApplicationStatus; daysAgo: number }[] = [
  { status: "applied", daysAgo: 16 },
  { status: "screening", daysAgo: 9 },
  { status: "interviewing", daysAgo: 2 },
];

const DOT_COLOR: Partial<Record<ApplicationStatus, string>> = {
  applied: "var(--color-status-applied)",
  screening: "var(--color-status-screening)",
  interviewing: "var(--color-status-interviewing)",
};

// Una sola secuencia al cargar (el historial se va llenando y el próximo paso llega
// el último); `motion-safe` la desactiva con "reducir movimiento".
const REVEAL =
  "motion-safe:animate-in motion-safe:fade-in-0 motion-safe:slide-in-from-bottom-1 motion-safe:duration-500 motion-safe:fill-mode-both";

const delay = (ms: number): CSSProperties => ({ animationDelay: `${ms}ms` });

export function AuthShowcase() {
  const { t, i18n } = useTranslation();
  const [today] = useState(() => Date.now());
  const shortDate = new Intl.DateTimeFormat(i18n.language, { day: "numeric", month: "short" });
  const weekdayDate = new Intl.DateTimeFormat(i18n.language, {
    weekday: "long",
    day: "numeric",
    month: "long",
  });

  return (
    <div className="grid w-full max-w-md" aria-hidden>
      {BACKGROUND_CARDS.map((card, index) => (
        <div
          key={card.company}
          className="flex items-center justify-between gap-3 rounded-xl px-5 py-3 text-card-foreground shadow-lg shadow-black/20"
          style={{
            marginInline: `${(BACKGROUND_CARDS.length - index) * 1.25}rem`,
            marginTop: index === 0 ? 0 : "-0.5rem",
            // Profundidad con tonos sólidos (cuanto más atrás, más índigo), no con
            // opacidad: con transparencia el texto se mezclaba con el panel.
            backgroundColor: `color-mix(in oklch, var(--card), var(--brand) ${(BACKGROUND_CARDS.length - index) * 8}%)`,
          }}
        >
          <p className="truncate text-sm">
            <span className="font-medium">{card.role}</span>
            <span className="text-muted-foreground"> {card.company}</span>
          </p>
          <ApplicationStatusBadge status={card.status} />
        </div>
      ))}

      <div className="-mt-2 rounded-xl bg-card p-5 text-card-foreground shadow-2xl shadow-black/40">
        <div className="flex items-start justify-between gap-3">
          <div className="grid gap-0.5">
            <p className="text-sm text-muted-foreground">Lumen Labs</p>
            <p className="text-lg font-semibold tracking-tight">Frontend Engineer</p>
          </div>
          <ApplicationStatusBadge status="interviewing" />
        </div>

        <ol className="mt-5 grid gap-3 border-l pl-5">
          {HISTORY.map((step, index) => (
            <li
              key={step.status}
              className={`relative flex items-center justify-between text-sm ${REVEAL}`}
              style={delay(200 + index * 250)}
            >
              <span
                className="absolute top-1/2 -left-[25px] size-2.5 -translate-y-1/2 rounded-full ring-4 ring-card"
                style={{ backgroundColor: DOT_COLOR[step.status] }}
              />
              <span>{t(`applications.status.${step.status}`)}</span>
              <span className="text-muted-foreground">
                {shortDate.format(today - step.daysAgo * DAY_MS)}
              </span>
            </li>
          ))}
        </ol>

        <div
          className={`mt-5 flex items-start gap-3 rounded-lg bg-accent px-4 py-3 text-accent-foreground ${REVEAL}`}
          style={delay(200 + HISTORY.length * 250 + 150)}
        >
          <BellRing className="mt-0.5 size-4 shrink-0" />
          <div className="grid gap-0.5 text-sm">
            <p className="font-medium">{t("auth.showcase.nextStep")}</p>
            <p>
              {t("auth.showcase.reminder", { date: weekdayDate.format(today + 2 * DAY_MS) })}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
