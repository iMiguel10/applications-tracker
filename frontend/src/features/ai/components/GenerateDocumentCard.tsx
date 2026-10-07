import { useState } from "react";
import { Loader2 } from "lucide-react";
import { useTranslation } from "react-i18next";

import { cn } from "@/shared/lib/utils";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { designName, uiCvLanguage } from "@/features/documents/lib/designName";
import type { CvDesign } from "@/features/documents/types/Document";

interface GenerateDocumentCardProps {
  /** Los diseños con etiquetas en el idioma de la propuesta. */
  designs: CvDesign[];
  defaultName: string;
  /** El CV dice si cada diseño es apto para ATS; la carta no lo necesita. */
  showAts: boolean;
  hint: string;
  submitLabel: string;
  /** Por qué no se puede generar todavía, ya traducido, o null. */
  problem: string | null;
  pending: boolean;
  onGenerate: (design: string, name: string | null) => void;
}

/** Elegir diseño y nombre y generar el PDF de una propuesta revisada. Lo comparten
 * el CV adaptado y la carta, que se maqueta con el diseño de un CV (0017). */
export function GenerateDocumentCard({
  designs,
  defaultName,
  showAts,
  hint,
  submitLabel,
  problem,
  pending,
  onGenerate,
}: GenerateDocumentCardProps) {
  const { t, i18n } = useTranslation();
  const [design, setDesign] = useState(
    ((showAts ? designs.find((item) => item.ats_friendly) : undefined) ?? designs[0])?.key ?? "",
  );
  const [name, setName] = useState(defaultName);
  const chosen = designs.find((item) => item.key === design);
  const uiLanguage = uiCvLanguage(i18n.language);

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("ai.review.generate")}</CardTitle>
        <CardDescription>{hint}</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        <fieldset className="grid gap-2">
          <legend className="mb-2 text-sm font-medium">{t("documents.generate.design")}</legend>
          <div className="grid gap-2 sm:grid-cols-2">
            {designs.map((item) => (
              <label
                key={item.key}
                className={cn(
                  "grid cursor-pointer gap-1 rounded-lg border p-3 text-sm transition-colors has-[:focus-visible]:ring-3 has-[:focus-visible]:ring-ring/50",
                  design === item.key ? "border-primary bg-primary/5" : "hover:bg-muted/50",
                )}
              >
                <span className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-2 font-medium">
                    <input
                      type="radio"
                      name="design"
                      value={item.key}
                      checked={design === item.key}
                      onChange={() => setDesign(item.key)}
                      className="accent-primary"
                    />
                    {designName(item, item.key, uiLanguage)}
                  </span>
                  {showAts && (
                    <Badge variant={item.ats_friendly ? "success" : "outline"}>
                      {t(
                        item.ats_friendly ? "documents.generate.ats" : "documents.generate.notAts",
                      )}
                    </Badge>
                  )}
                </span>
              </label>
            ))}
          </div>
        </fieldset>
        {showAts && chosen && !chosen.ats_friendly && (
          <p className="text-sm text-amber-800 dark:text-amber-300">
            {t("documents.generate.notAtsWarning")}
          </p>
        )}
        <div className="grid gap-2 sm:max-w-md">
          <Label htmlFor="ai-document-name">{t("documents.fields.name")}</Label>
          <Input
            id="ai-document-name"
            value={name}
            maxLength={200}
            onChange={(event) => setName(event.target.value)}
          />
        </div>
        {problem && <p className="text-sm text-destructive">{problem}</p>}
        <div>
          <Button
            onClick={() => onGenerate(design, name.trim() || null)}
            disabled={!!problem || !design || pending}
          >
            {pending && <Loader2 className="animate-spin" />}
            {submitLabel}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
