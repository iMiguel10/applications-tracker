import { Pencil, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { Button } from "@/shared/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/shared/components/ui/table";
import type { Company } from "../types/Company";

interface CompaniesTableProps {
  companies: Company[];
  onEdit: (company: Company) => void;
  onDelete: (company: Company) => void;
}

export function CompaniesTable({ companies, onEdit, onDelete }: CompaniesTableProps) {
  const { t } = useTranslation();

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>{t("companies.fields.name")}</TableHead>
          <TableHead>{t("companies.fields.location")}</TableHead>
          <TableHead>{t("companies.fields.website")}</TableHead>
          <TableHead className="text-right">{t("companies.applicationsCount")}</TableHead>
          <TableHead className="w-24" />
        </TableRow>
      </TableHeader>
      <TableBody>
        {companies.map((company) => (
          <TableRow key={company.id}>
            <TableCell className="font-medium">{company.name}</TableCell>
            <TableCell>{company.location ?? "—"}</TableCell>
            <TableCell>
              {company.website ? (
                <a
                  href={company.website}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="underline underline-offset-2"
                >
                  {new URL(company.website).hostname}
                </a>
              ) : (
                "—"
              )}
            </TableCell>
            <TableCell className="text-right">
              {company.applications_count > 0 ? (
                <Link
                  to={`/applications?company_id=${company.id}&archived=all`}
                  className="underline underline-offset-2"
                >
                  {company.applications_count}
                </Link>
              ) : (
                0
              )}
            </TableCell>
            <TableCell>
              <div className="flex justify-end gap-1">
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label={t("common.edit")}
                  onClick={() => onEdit(company)}
                >
                  <Pencil />
                </Button>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label={t("common.delete")}
                  onClick={() => onDelete(company)}
                >
                  <Trash2 />
                </Button>
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
