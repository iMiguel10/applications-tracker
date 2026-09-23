import { useTranslation } from "react-i18next";
import { Bar, BarChart, CartesianGrid, Cell, XAxis, YAxis } from "recharts";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import type { ApplicationStatus } from "@/features/applications/types/Application";
import type { StatusCount } from "../types/Dashboard";

// Un color por estado, en el orden "natural" del proceso (igual que el resto de la
// interfaz), no uno por serie: aquí solo hay una serie (el recuento).
const COLORS: Record<ApplicationStatus, string> = {
  saved: "var(--color-chart-1)",
  applied: "var(--color-chart-2)",
  screening: "var(--color-chart-2)",
  interviewing: "var(--color-chart-3)",
  offer: "var(--color-chart-4)",
  accepted: "var(--color-chart-4)",
  rejected: "var(--color-chart-5)",
  withdrawn: "var(--color-chart-5)",
};

export function StatusBreakdownCard({ statusCounts }: { statusCounts: StatusCount[] }) {
  const { t } = useTranslation();
  const data = statusCounts.map((row) => ({
    status: row.status,
    label: t(`applications.status.${row.status}`),
    count: row.count,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("dashboard.statusBreakdown.title")}</CardTitle>
      </CardHeader>
      <CardContent>
        <BarChart
          width={480}
          height={260}
          data={data}
          layout="vertical"
          margin={{ left: 8, right: 16 }}
          className="max-w-full"
        >
          <CartesianGrid horizontal={false} stroke="var(--color-border)" />
          <XAxis type="number" allowDecimals={false} stroke="var(--color-muted-foreground)" />
          <YAxis
            type="category"
            dataKey="label"
            width={90}
            stroke="var(--color-muted-foreground)"
          />
          <Bar dataKey="count" radius={4}>
            {data.map((row) => (
              <Cell key={row.status} fill={COLORS[row.status]} />
            ))}
          </Bar>
        </BarChart>
      </CardContent>
    </Card>
  );
}
