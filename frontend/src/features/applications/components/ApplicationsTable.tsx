import { Archive, Eye } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { formatDateOnly } from "@/shared/lib/format";
import { buttonVariants } from "@/shared/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/shared/components/ui/table";
import type { Application } from "../types/Application";
import { ApplicationStatusBadge } from "./ApplicationStatusBadge";

export function ApplicationsTable({ applications }: { applications: Application[] }) {
  const { t, i18n } = useTranslation();

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>{t("applications.fields.position")}</TableHead>
          <TableHead>{t("applications.fields.company")}</TableHead>
          <TableHead>{t("applications.fields.status")}</TableHead>
          <TableHead>{t("applications.fields.appliedAt")}</TableHead>
          <TableHead>{t("applications.fields.workMode")}</TableHead>
          <TableHead className="w-12" />
        </TableRow>
      </TableHeader>
      <TableBody>
        {applications.map((application) => (
          <TableRow key={application.id}>
            <TableCell className="font-medium">
              <Link to={`/applications/${application.id}`} className="hover:underline">
                {application.position_title}
              </Link>
              {application.archived_at && (
                <Archive
                  className="ml-2 inline size-3.5 text-muted-foreground"
                  aria-label={t("applications.archived")}
                />
              )}
            </TableCell>
            <TableCell>{application.company.name}</TableCell>
            <TableCell>
              <ApplicationStatusBadge status={application.status} />
            </TableCell>
            <TableCell>{formatDateOnly(application.applied_at, i18n.language)}</TableCell>
            <TableCell>
              {application.work_mode ? t(`applications.workMode.${application.work_mode}`) : "—"}
            </TableCell>
            <TableCell>
              <Link
                to={`/applications/${application.id}`}
                className={buttonVariants({ variant: "ghost", size: "icon-sm" })}
                aria-label={t("common.view")}
              >
                <Eye />
              </Link>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
