import { useTranslation } from "react-i18next";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import type { ResponseRate } from "../types/Dashboard";

// RF-66: mismo umbral que el backend, solo para el mensaje. La decisión de si se
// muestra el porcentaje (rate: number | null) siempre la toma la API.
const MIN_SAMPLE_FOR_RATE = 5;

export function ResponseRateCard({ responseRate }: { responseRate: ResponseRate }) {
  const { t, i18n } = useTranslation();
  const { sent_count: sent, reached_count: reached, rate } = responseRate;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("dashboard.responseRate.title")}</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-2">
        {rate === null ? (
          <p className="text-muted-foreground">
            {t("dashboard.responseRate.insufficientData", { min: MIN_SAMPLE_FOR_RATE, sent })}
          </p>
        ) : (
          <>
            <span className="text-4xl font-semibold">
              {new Intl.NumberFormat(i18n.language, { style: "percent" }).format(rate)}
            </span>
            <p className="text-sm text-muted-foreground">
              {t("dashboard.responseRate.description", { reached, sent })}
            </p>
          </>
        )}
      </CardContent>
    </Card>
  );
}
