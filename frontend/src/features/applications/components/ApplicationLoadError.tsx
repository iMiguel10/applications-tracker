import { ArrowLeft, FileQuestion } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { ApiError } from "@/shared/lib/apiClient";
import { buttonVariants } from "@/shared/components/ui/button";
import { EmptyState } from "@/shared/components/common/EmptyState";
import { ErrorState } from "@/shared/components/common/ErrorState";

interface ApplicationLoadErrorProps {
  error: Error | null;
  onRetry: () => void;
  retrying: boolean;
}

/** Un 404 (no existe, o es de otro usuario: invariante 2) no se arregla reintentando:
 * se ofrece volver al listado. Cualquier otro fallo sí se puede reintentar. */
export function ApplicationLoadError({ error, onRetry, retrying }: ApplicationLoadErrorProps) {
  const { t } = useTranslation();

  if (error instanceof ApiError && error.status === 404) {
    return (
      <EmptyState
        icon={FileQuestion}
        title={t("applications.notFound")}
        action={
          <Link to="/applications" className={buttonVariants({ variant: "outline" })}>
            <ArrowLeft />
            {t("applications.backToList")}
          </Link>
        }
      />
    );
  }

  return <ErrorState onRetry={onRetry} retrying={retrying} />;
}
