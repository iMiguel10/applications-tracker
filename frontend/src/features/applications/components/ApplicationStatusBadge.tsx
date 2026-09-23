import { useTranslation } from "react-i18next";
import { Badge } from "@/shared/components/ui/badge";
import type { ApplicationStatus } from "../types/Application";

// Cada etapa toma el color de familia que le pide la identidad visual (F8.4):
// "Guardada" en ámbar (la única que de verdad está pendiente de una acción, enviarla),
// Enviada en índigo, En revisión en violeta, Entrevistas en sky, y Oferta/Aceptada
// comparten esmeralda (`--success`) como cierre positivo. Descartada usa el rojo de
// `--destructive` y Retirada queda en el gris neutro de `--muted`.
const STATUS_CLASSES: Record<ApplicationStatus, string> = {
  saved: "border-transparent bg-status-saved/10 text-status-saved",
  applied: "border-transparent bg-status-applied/10 text-status-applied",
  screening: "border-transparent bg-status-screening/10 text-status-screening",
  interviewing: "border-transparent bg-status-interviewing/10 text-status-interviewing",
  offer: "border-transparent bg-success/10 text-success-text",
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
