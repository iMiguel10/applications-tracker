import { ArrowRight, CircleAlert, CircleCheck, CircleMinus, CircleX } from "lucide-react";
import { useTranslation } from "react-i18next";

import { cn } from "@/shared/lib/utils";
import { Badge } from "@/shared/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import {
  evidenceLabels,
  type CvSource,
  type OfferMatch,
  type RequirementMatch,
  type RequirementState,
} from "../lib/match";

const ICONS: Record<RequirementState, typeof CircleCheck> = {
  covered: CircleCheck,
  unnamed: CircleAlert,
  dropped: CircleMinus,
  missing: CircleX,
};

const ICON_COLORS: Record<RequirementState, string> = {
  covered: "text-emerald-600 dark:text-emerald-400",
  unnamed: "text-amber-600 dark:text-amber-400",
  dropped: "text-amber-600 dark:text-amber-400",
  missing: "text-muted-foreground",
};

/**
 * Encaje con la oferta: el porcentaje con el perfil tal cual y con el CV tal como
 * queda en la revisión, que cambia al editar. Debajo, cada requisito y qué hacer
 * para que cuente. Lo que el perfil demuestra con otras palabras nunca suma: se
 * enseña la evidencia para que decida la persona (la IA puede ser generosa).
 */
export function OfferMatchCard({ match, source }: { match: OfferMatch; source: CvSource }) {
  const { t } = useTranslation();
  const toImprove = match.requirements.filter(
    (item) => item.state === "unnamed" || item.state === "dropped",
  ).length;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("ai.match.title")}</CardTitle>
        <CardDescription>{t("ai.match.description")}</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-5">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
          <Score label={t("ai.match.before")} value={match.before} muted />
          <ArrowRight className="size-5 text-muted-foreground" aria-hidden />
          <div aria-live="polite">
            <Score label={t("ai.match.after")} value={match.after} />
          </div>
        </div>
        {toImprove > 0 && (
          <p className="text-sm text-amber-800 dark:text-amber-300">
            {t("ai.match.toImprove", { count: toImprove })}
          </p>
        )}

        <ul className="grid gap-3" aria-label={t("ai.match.requirements")}>
          {match.requirements.map((item) => (
            <RequirementRow key={item.requirement.name} item={item} source={source} />
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

function Score({ label, value, muted = false }: { label: string; value: number; muted?: boolean }) {
  return (
    <div className="grid gap-1">
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      <span
        className={cn(
          "text-3xl font-semibold tabular-nums",
          muted ? "text-muted-foreground" : "text-foreground",
        )}
      >
        {value} %
      </span>
      <span className="h-1.5 w-32 overflow-hidden rounded-full bg-muted" aria-hidden>
        <span
          className={cn(
            "block h-full rounded-full",
            muted ? "bg-muted-foreground/50" : "bg-primary",
          )}
          style={{ width: `${value}%` }}
        />
      </span>
    </div>
  );
}

function RequirementRow({ item, source }: { item: RequirementMatch; source: CvSource }) {
  const { t } = useTranslation();
  const { requirement, state } = item;
  const Icon = ICONS[state];
  const evidence = state === "unnamed" ? evidenceLabels(requirement, source) : [];

  return (
    <li className="flex gap-3 text-sm">
      <Icon className={cn("mt-0.5 size-4 shrink-0", ICON_COLORS[state])} aria-hidden />
      <div className="grid min-w-0 gap-1">
        <p className="flex flex-wrap items-center gap-2">
          <span className="font-medium">{requirement.name}</span>
          <Badge variant={requirement.importance === "required" ? "secondary" : "outline"}>
            {t(`ai.match.importance.${requirement.importance}`)}
          </Badge>
          <span className="sr-only">{t(`ai.match.states.${state}`)}</span>
        </p>
        {state !== "covered" && (
          <p className="text-muted-foreground">
            {state === "missing" && requirement.note
              ? requirement.note
              : t(`ai.match.hints.${state}`)}
          </p>
        )}
        {evidence.length > 0 && (
          <ul className="grid gap-1 text-muted-foreground">
            {evidence.map((label) => (
              <li key={label} className="rounded-md bg-muted/50 px-2 py-1">
                {label}
              </li>
            ))}
          </ul>
        )}
        {(state === "unnamed" || state === "dropped") && (
          <p className="text-xs text-muted-foreground">
            {t("ai.match.keywords", {
              keywords: requirement.keywords.join(", "),
            })}
          </p>
        )}
      </div>
    </li>
  );
}
