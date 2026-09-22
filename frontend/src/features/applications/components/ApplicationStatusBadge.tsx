import { useTranslation } from "react-i18next";
import { Badge } from "@/shared/components/ui/badge";
import type { ApplicationStatus } from "../types/Application";

const VARIANTS: Record<ApplicationStatus, "default" | "secondary" | "outline" | "destructive"> = {
  saved: "outline",
  applied: "secondary",
  screening: "secondary",
  interviewing: "default",
  offer: "default",
  accepted: "default",
  rejected: "destructive",
  withdrawn: "outline",
};

export function ApplicationStatusBadge({ status }: { status: ApplicationStatus }) {
  const { t } = useTranslation();
  return <Badge variant={VARIANTS[status]}>{t(`applications.status.${status}`)}</Badge>;
}
