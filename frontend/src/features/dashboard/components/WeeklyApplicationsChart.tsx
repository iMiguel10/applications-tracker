import { useTranslation } from "react-i18next";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { ChartTooltip } from "./ChartTooltip";
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
  type WeekRow = (typeof data)[number];

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("dashboard.weeklyApplications.title")}</CardTitle>
      </CardHeader>
      <CardContent className="h-65">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8 }}>
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
            <Tooltip
              cursor={{ fill: "var(--color-muted)" }}
              content={
                <ChartTooltip
                  formatLabel={(row: WeekRow) => row.week}
                  formatValue={(row: WeekRow) =>
                    t("dashboard.weeklyApplications.tooltip", { count: row.count })
                  }
                />
              }
            />
            <Bar
              dataKey="count"
              fill="var(--color-chart-1)"
              radius={4}
              maxBarSize={32}
              activeBar={{ fill: "var(--color-chart-2)" }}
            />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
