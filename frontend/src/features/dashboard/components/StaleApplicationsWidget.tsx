import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import type { StaleApplication } from "../types/Dashboard";

interface StaleApplicationsWidgetProps {
  applications: StaleApplication[];
  total: number;
  afterDays: number;
}

// RF-65: nunca se presenta como descartada, solo como "sin actividad desde hace
// N días" — el sistema no sabe si la empresa respondió y el usuario no lo registró.
export function StaleApplicationsWidget({
  applications,
  total,
  afterDays,
}: StaleApplicationsWidgetProps) {
  const { t } = useTranslation();
  const extra = total - applications.length;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("dashboard.staleApplications.title")}</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3">
        {applications.length === 0 && (
          <p className="text-muted-foreground">
            {t("dashboard.staleApplications.empty", { days: afterDays })}
          </p>
        )}
        {applications.length > 0 && (
          <ul className="grid gap-2">
            {applications.map((stale) => (
              <li key={stale.application.id} className="grid gap-0.5">
                <Link
                  to={`/applications/${stale.application.id}`}
                  className="font-medium underline underline-offset-2 hover:text-foreground"
                >
                  {stale.application.position_title} · {stale.application.company.name}
                </Link>
                <span className="text-sm text-muted-foreground">
                  {t("dashboard.staleApplications.sinceDays", {
                    days: stale.days_since_activity,
                  })}
                </span>
              </li>
            ))}
          </ul>
        )}
        {extra > 0 && (
          <p className="text-sm text-muted-foreground">
            {t("dashboard.staleApplications.more", { count: extra })}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
