import { useTranslation } from "react-i18next";

import { Button } from "@/shared/components/ui/button";
import { useApplications } from "../hooks/queries/useApplications";

interface ApplicationsListProps {
  page: number;
  limit: number;
  onPageChange: (page: number) => void;
}

export function ApplicationsList({ page, limit, onPageChange }: ApplicationsListProps) {
  const { t, i18n } = useTranslation();
  const { data, isLoading, isError } = useApplications({ page, limit });

  if (isLoading) return <p className="text-muted-foreground">{t("common.loading")}</p>;
  if (isError || !data) return <p className="text-destructive">{t("applications.loadError")}</p>;
  if (data.total === 0) return <p className="text-muted-foreground">{t("applications.empty")}</p>;

  const dateFormatter = new Intl.DateTimeFormat(i18n.language, {
    dateStyle: "medium",
    timeStyle: "short",
  });

  return (
    <div className="grid gap-3">
      <ul className="divide-y rounded-lg border">
        {data.items.map((application) => (
          <li key={application.id} className="flex items-baseline justify-between gap-4 p-3">
            <div>
              <p className="font-medium">{application.position_title}</p>
              <p className="text-sm text-muted-foreground">{application.company_name}</p>
            </div>
            <time dateTime={application.created_at} className="text-sm text-muted-foreground">
              {dateFormatter.format(new Date(application.created_at))}
            </time>
          </li>
        ))}
      </ul>

      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">
          {t("common.pagination", { page: data.page, pages: data.pages, total: data.total })}
        </span>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
            {t("common.previous")}
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= data.pages}
            onClick={() => onPageChange(page + 1)}
          >
            {t("common.next")}
          </Button>
        </div>
      </div>
    </div>
  );
}
