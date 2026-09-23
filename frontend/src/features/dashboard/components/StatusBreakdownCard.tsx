import { useTranslation } from "react-i18next";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import type { ApplicationStatus } from "@/features/applications/types/Application";
import { ChartTooltip } from "./ChartTooltip";
import type { StatusCount } from "../types/Dashboard";

// Los mismos tokens que ApplicationStatusBadge, no los genéricos --chart-*: así una
// barra y una insignia del mismo estado siempre coinciden.
const COLORS: Record<ApplicationStatus, string> = {
  saved: "var(--color-status-saved)",
  applied: "var(--color-status-applied)",
  screening: "var(--color-status-screening)",
  interviewing: "var(--color-status-interviewing)",
  offer: "var(--color-success)",
  accepted: "var(--color-success)",
  rejected: "var(--color-destructive)",
  withdrawn: "var(--color-muted-foreground)",
};

export function StatusBreakdownCard({ statusCounts }: { statusCounts: StatusCount[] }) {
  const { t } = useTranslation();
  const data = statusCounts.map((row) => ({
    status: row.status,
    label: t(`applications.status.${row.status}`),
    count: row.count,
  }));
  type StatusRow = (typeof data)[number];

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("dashboard.statusBreakdown.title")}</CardTitle>
      </CardHeader>
      <CardContent className="h-65">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{ left: 8, right: 16 }}
          >
            <CartesianGrid horizontal={false} stroke="var(--color-border)" />
            <XAxis type="number" allowDecimals={false} stroke="var(--color-muted-foreground)" />
            <YAxis
              type="category"
              dataKey="label"
              width={90}
              stroke="var(--color-muted-foreground)"
            />
            <Tooltip
              cursor={{ fill: "var(--color-muted)" }}
              content={
                <ChartTooltip
                  formatLabel={(row: StatusRow) => row.label}
                  formatValue={(row: StatusRow) =>
                    t("dashboard.statusBreakdown.tooltip", { count: row.count })
                  }
                />
              }
            />
            <Bar dataKey="count" radius={4} maxBarSize={28} activeBar={{ fillOpacity: 0.8 }}>
              {data.map((row) => (
                <Cell key={row.status} fill={COLORS[row.status]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
