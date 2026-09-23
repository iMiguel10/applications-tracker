import { useTranslation } from "react-i18next";
import { Badge } from "@/shared/components/ui/badge";
import type { ApplicationStatus } from "../types/Application";

// Progresión de color con sentido narrativo (arquitectura §6): azul → índigo →
// violeta → ámbar antes de cerrar en éxito (verde) o descarte (rojo). "Guardada" y
// "Retirada" quedan neutras: aún no ha empezado o ya no está en juego.
const STATUS_CLASSES: Record<ApplicationStatus, string> = {
  saved: "border-border bg-transparent text-muted-foreground",
  applied: "border-transparent bg-status-applied/10 text-status-applied",
  screening: "border-transparent bg-status-screening/10 text-status-screening",
  interviewing: "border-transparent bg-status-interviewing/10 text-status-interviewing",
  offer: "border-transparent bg-status-offer/10 text-status-offer",
  accepted: "border-transparent bg-success/10 text-success-text",
  rejected: "border-transparent bg-destructive/10 text-destructive",
  withdrawn: "border-transparent bg-muted text-muted-foreground",
};

export function ApplicationStatusBadge({ status }: { status: ApplicationStatus }) {
  const { t } = useTranslation();
  return (
    <Badge variant="outline" className={STATUS_CLASSES[status]}>
      {t(`applications.status.${status}`)}
    </Badge>
  );
}
