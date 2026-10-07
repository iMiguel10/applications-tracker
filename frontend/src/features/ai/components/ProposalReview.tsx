import { ArrowDown, ArrowUp, Trash2, X } from "lucide-react";
import { useTranslation } from "react-i18next";

import { cn } from "@/shared/lib/utils";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Textarea } from "@/shared/components/ui/textarea";
import { formatMonth } from "@/features/profile/lib/months";
import type { ProfileEntry } from "@/features/profile/types/ProfileEntry";
import {
  BULLET_MAX_LENGTH,
  isRewritten,
  SUMMARY_MAX_LENGTH,
  type ReviewExperience,
  type ReviewState,
} from "../lib/review";
import type { ProposedGap } from "../types/Ai";

interface ProposalReviewProps {
  state: ReviewState;
  onChange: (state: ReviewState) => void;
  /** El resumen del perfil, para compararlo con el propuesto. */
  profileSummary: string | null;
  /** null: no se enseñan aquí (las propuestas con requisitos las enseñan en el
   * encaje con la oferta). */
  gaps: ProposedGap[] | null;
}

/**
 * La propuesta, editable y junto a lo que dice el perfil (RF-113, RF-118): cada
 * logro reformulado al lado de su original, para que una exageración se vea a
 * simple vista. Se puede reescribir, quitar y reordenar; no añadir: lo que no está
 * en el perfil no puede salir en el CV (RF-111).
 */
export function ProposalReview({ state, onChange, profileSummary, gaps }: ProposalReviewProps) {
  const { t } = useTranslation();

  const setExperiences = (experiences: ReviewExperience[]) => onChange({ ...state, experiences });
  const move = (index: number, step: -1 | 1) => {
    const next = [...state.experiences];
    [next[index], next[index + step]] = [next[index + step], next[index]];
    setExperiences(next);
  };

  return (
    <div className="grid gap-6">
      <Card>
        <CardHeader>
          <CardTitle>{t("ai.review.summary")}</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 lg:grid-cols-2">
          <Original
            label={t("ai.review.inProfile")}
            text={profileSummary ?? t("ai.review.noProfileSummary")}
          />
          <Proposed
            id="summary"
            label={t("ai.review.proposed")}
            value={state.summary}
            max={SUMMARY_MAX_LENGTH}
            rows={5}
            onChange={(summary) => onChange({ ...state, summary })}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t("ai.review.experience")}</CardTitle>
          <CardDescription>{t("ai.review.experienceHint")}</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-6">
          {state.experiences.length === 0 && (
            <p className="text-sm text-destructive">{t("ai.review.noExperience")}</p>
          )}
          {state.experiences.map((experience, index) => (
            <section
              key={experience.entryId}
              aria-label={experience.entry?.title ?? t("ai.review.missing")}
              className="grid gap-3 border-t pt-4 first:border-t-0 first:pt-0"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <EntryHeading entry={experience.entry} />
                <div className="flex gap-1">
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    aria-label={t("ai.review.moveUp")}
                    disabled={index === 0}
                    onClick={() => move(index, -1)}
                  >
                    <ArrowUp />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    aria-label={t("ai.review.moveDown")}
                    disabled={index === state.experiences.length - 1}
                    onClick={() => move(index, 1)}
                  >
                    <ArrowDown />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    aria-label={t("ai.review.removeExperience")}
                    onClick={() =>
                      setExperiences(state.experiences.filter((item) => item !== experience))
                    }
                  >
                    <Trash2 />
                  </Button>
                </div>
              </div>

              {experience.bullets.length === 0 && (
                <p className="text-sm text-muted-foreground">{t("ai.review.noBullets")}</p>
              )}
              <ul className="grid gap-4">
                {experience.bullets.map((bullet, bulletIndex) => (
                  <li key={bullet.bulletId} className="grid gap-2 lg:grid-cols-2 lg:gap-4">
                    <Original label={t("ai.review.inProfile")} text={bullet.original} />
                    <div className="grid gap-1.5">
                      <div className="flex items-center justify-between gap-2">
                        <span className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
                          {t("ai.review.proposed")}
                          {isRewritten(bullet) && (
                            <Badge variant="secondary">{t("ai.review.rewritten")}</Badge>
                          )}
                        </span>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          aria-label={t("ai.review.removeBullet")}
                          onClick={() =>
                            setExperiences(
                              state.experiences.map((item) =>
                                item === experience
                                  ? {
                                      ...item,
                                      bullets: item.bullets.filter((b) => b !== bullet),
                                    }
                                  : item,
                              ),
                            )
                          }
                        >
                          <X />
                        </Button>
                      </div>
                      <Textarea
                        aria-label={t("ai.review.bulletLabel", {
                          entry: experience.entry?.title ?? "",
                          index: bulletIndex + 1,
                        })}
                        value={bullet.text}
                        maxLength={BULLET_MAX_LENGTH}
                        rows={2}
                        className={cn(!bullet.text.trim() && "border-destructive")}
                        onChange={(event) =>
                          setExperiences(
                            state.experiences.map((item) =>
                              item === experience
                                ? {
                                    ...item,
                                    bullets: item.bullets.map((b) =>
                                      b === bullet ? { ...b, text: event.target.value } : b,
                                    ),
                                  }
                                : item,
                            ),
                          )
                        }
                      />
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t("ai.review.skills")}</CardTitle>
          <CardDescription>{t("ai.review.skillsHint")}</CardDescription>
        </CardHeader>
        <CardContent>
          {state.skills.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t("ai.review.noSkills")}</p>
          ) : (
            <ul className="flex flex-wrap gap-2">
              {state.skills.map((skill) => (
                <li key={skill.id}>
                  <Badge variant={skill.name ? "outline" : "destructive"} className="gap-1 pr-1">
                    {skill.name ?? t("ai.review.missing")}
                    <button
                      type="button"
                      aria-label={t("ai.review.removeSkill", { skill: skill.name ?? "" })}
                      className="rounded-sm p-0.5 hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:outline-none"
                      onClick={() =>
                        onChange({ ...state, skills: state.skills.filter((s) => s !== skill) })
                      }
                    >
                      <X className="size-3" />
                    </button>
                  </Badge>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {gaps && (
        <Card>
          <CardHeader>
            <CardTitle>{t("ai.review.gaps")}</CardTitle>
            <CardDescription>{t("ai.review.gapsHint")}</CardDescription>
          </CardHeader>
          <CardContent>
            {gaps.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t("ai.review.noGaps")}</p>
            ) : (
              <ul className="grid gap-2 text-sm">
                {gaps.map((gap) => (
                  <li key={gap.requirement}>
                    <span className="font-medium">{gap.requirement}</span>
                    {gap.note && <span className="text-muted-foreground">: {gap.note}</span>}
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function EntryHeading({ entry }: { entry: ProfileEntry | null }) {
  const { t, i18n } = useTranslation();
  if (!entry) {
    return <p className="font-medium text-destructive">{t("ai.review.missing")}</p>;
  }
  const locale = i18n.resolvedLanguage ?? "es";
  const start = entry.start_date ? formatMonth(entry.start_date, locale) : null;
  const end = entry.is_current
    ? t("profile.entries.present")
    : entry.end_date
      ? formatMonth(entry.end_date, locale)
      : null;
  const dates = start && end ? `${start} – ${end}` : (start ?? end);
  return (
    <div className="min-w-0">
      <p className="font-medium">
        {entry.title}
        {entry.organization && (
          <span className="font-normal text-muted-foreground"> · {entry.organization}</span>
        )}
      </p>
      {dates && <p className="text-sm text-muted-foreground">{dates}</p>}
    </div>
  );
}

function Original({ label, text }: { label: string; text: string | null }) {
  const { t } = useTranslation();
  return (
    <div className="grid content-start gap-1.5">
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      <p
        className={cn(
          "rounded-md bg-muted/50 px-3 py-2 text-sm whitespace-pre-wrap",
          text === null && "text-destructive",
        )}
      >
        {text ?? t("ai.review.missing")}
      </p>
    </div>
  );
}

function Proposed({
  id,
  label,
  value,
  max,
  rows,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  max: number;
  rows: number;
  onChange: (value: string) => void;
}) {
  return (
    <div className="grid content-start gap-1.5">
      <label htmlFor={id} className="text-xs font-medium text-muted-foreground">
        {label}
      </label>
      <Textarea
        id={id}
        value={value}
        maxLength={max}
        rows={rows}
        className={cn(!value.trim() && "border-destructive")}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  );
}
