import { useTranslation } from "react-i18next";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import type { WeeklyApplications } from "../types/Dashboard";

export function WeeklyApplicationsChart({
  applicationsPerWeek,
}: {
  applicationsPerWeek: WeeklyApplications[];
}) {
  const { t, i18n } = useTranslation();
  const data = applicationsPerWeek.map((week) => ({
    week: new Intl.DateTimeFormat(i18n.language, { day: "numeric", month: "short" }).format(
      new Date(`${week.week_start}T00:00:00`),
    ),
    count: week.count,
    weekStart: week.week_start,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("dashboard.weeklyApplications.title")}</CardTitle>
      </CardHeader>
      <CardContent>
        <BarChart width={480} height={260} data={data} className="max-w-full">
          <CartesianGrid vertical={false} stroke="var(--color-border)" />
          <XAxis
            dataKey="week"
            interval={1}
            tick={{ fontSize: 12 }}
            stroke="var(--color-muted-foreground)"
          />
          <YAxis
            allowDecimals={false}
            width={28}
            stroke="var(--color-muted-foreground)"
          />
          <Bar dataKey="count" fill="var(--color-chart-1)" radius={4} />
        </BarChart>
      </CardContent>
    </Card>
  );
}
