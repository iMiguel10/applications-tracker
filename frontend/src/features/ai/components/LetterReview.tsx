import { ArrowDown, ArrowUp, CircleAlert, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";

import { cn } from "@/shared/lib/utils";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { Button } from "@/shared/components/ui/button";
import { Textarea } from "@/shared/components/ui/textarea";
import {
  LETTER_LINE_MAX_LENGTH,
  LETTER_PARAGRAPH_MAX_LENGTH,
  wordCount,
  type LetterState,
  type ReviewParagraph,
} from "../lib/letter";
import { referenceLabels, type CvSource } from "../lib/match";

interface LetterReviewProps {
  state: LetterState;
  onChange: (state: LetterState) => void;
  source: CvSource;
}

/**
 * La carta, editable, con cada párrafo junto a lo que dice el perfil en que se
 * apoya (ia.md §5). La carta es casi toda texto libre: un párrafo sin apoyo se
 * marca para leerlo con más cuidado. Se puede reescribir, quitar y reordenar.
 */
export function LetterReview({ state, onChange, source }: LetterReviewProps) {
  const { t } = useTranslation();
  const setParagraphs = (paragraphs: ReviewParagraph[]) => onChange({ ...state, paragraphs });
  const move = (index: number, step: -1 | 1) => {
    const next = [...state.paragraphs];
    [next[index], next[index + step]] = [next[index + step], next[index]];
    setParagraphs(next);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("ai.letter.title")}</CardTitle>
        <CardDescription>{t("ai.letter.hint")}</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-6">
        <div className="grid gap-2 sm:max-w-md">
          <Label htmlFor="letter-greeting">{t("ai.letter.greeting")}</Label>
          <Input
            id="letter-greeting"
            value={state.greeting}
            maxLength={LETTER_LINE_MAX_LENGTH}
            aria-invalid={!state.greeting.trim()}
            onChange={(event) => onChange({ ...state, greeting: event.target.value })}
          />
        </div>

        {state.paragraphs.length === 0 && (
          <p className="text-sm text-destructive">{t("ai.letter.noParagraphs")}</p>
        )}
        <ol className="grid gap-6">
          {state.paragraphs.map((paragraph, index) => {
            const labels = referenceLabels(paragraph.sources, source);
            const id = `letter-paragraph-${paragraph.key}`;
            return (
              <li
                key={paragraph.key}
                className="grid gap-3 border-t pt-4 first:border-t-0 first:pt-0 lg:grid-cols-[minmax(0,1fr)_18rem] lg:gap-6"
              >
                <div className="grid content-start gap-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <label htmlFor={id} className="text-xs font-medium text-muted-foreground">
                      {t("ai.letter.paragraph", { index: index + 1 })}
                    </label>
                    <div className="flex gap-1">
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        aria-label={t("ai.letter.moveUp", { index: index + 1 })}
                        disabled={index === 0}
                        onClick={() => move(index, -1)}
                      >
                        <ArrowUp />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        aria-label={t("ai.letter.moveDown", { index: index + 1 })}
                        disabled={index === state.paragraphs.length - 1}
                        onClick={() => move(index, 1)}
                      >
                        <ArrowDown />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        aria-label={t("ai.letter.remove", { index: index + 1 })}
                        onClick={() =>
                          setParagraphs(state.paragraphs.filter((item) => item !== paragraph))
                        }
                      >
                        <Trash2 />
                      </Button>
                    </div>
                  </div>
                  <Textarea
                    id={id}
                    value={paragraph.text}
                    maxLength={LETTER_PARAGRAPH_MAX_LENGTH}
                    rows={4}
                    className={cn(!paragraph.text.trim() && "border-destructive")}
                    onChange={(event) =>
                      setParagraphs(
                        state.paragraphs.map((item) =>
                          item === paragraph ? { ...item, text: event.target.value } : item,
                        ),
                      )
                    }
                  />
                </div>
                <div className="grid content-start gap-1.5 text-sm">
                  <span className="text-xs font-medium text-muted-foreground">
                    {t("ai.letter.sources")}
                  </span>
                  {labels.length > 0 ? (
                    <ul className="grid gap-1 text-muted-foreground">
                      {labels.map((label) => (
                        <li key={label} className="rounded-md bg-muted/50 px-2 py-1">
                          {label}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="flex items-start gap-1.5 text-amber-800 dark:text-amber-300">
                      <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
                      {t("ai.letter.noSources")}
                    </p>
                  )}
                </div>
              </li>
            );
          })}
        </ol>

        <div className="grid gap-2 sm:max-w-md">
          <Label htmlFor="letter-closing">{t("ai.letter.closing")}</Label>
          <Input
            id="letter-closing"
            value={state.closing}
            maxLength={LETTER_LINE_MAX_LENGTH}
            aria-invalid={!state.closing.trim()}
            onChange={(event) => onChange({ ...state, closing: event.target.value })}
          />
        </div>
        <p className="text-xs text-muted-foreground">
          {t("ai.letter.words", { count: wordCount(state) })}
        </p>
      </CardContent>
    </Card>
  );
}
