import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { formatDateTime } from "@/shared/lib/format";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import type { UpcomingInterview } from "../types/Dashboard";

interface UpcomingInterviewsWidgetProps {
  interviews: UpcomingInterview[];
  total: number;
}

export function UpcomingInterviewsWidget({ interviews, total }: UpcomingInterviewsWidgetProps) {
  const { t, i18n } = useTranslation();
  const extra = total - interviews.length;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("dashboard.upcomingInterviews.title")}</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3">
        {interviews.length === 0 && (
          <p className="text-muted-foreground">{t("dashboard.upcomingInterviews.empty")}</p>
        )}
        {interviews.length > 0 && (
          <ul className="grid gap-2">
            {interviews.map((interview) => (
              <li key={interview.id} className="grid gap-0.5">
                <Link
                  to={`/applications/${interview.application.id}`}
                  className="font-medium underline underline-offset-2 hover:text-foreground"
                >
                  {interview.application.position_title} · {interview.application.company.name}
                </Link>
                <span className="text-sm text-muted-foreground">
                  {formatDateTime(interview.scheduled_at, i18n.language)}
                </span>
              </li>
            ))}
          </ul>
        )}
        {extra > 0 && (
          <p className="text-sm text-muted-foreground">
            {t("dashboard.upcomingInterviews.more", { count: extra })}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
