import { useEffect, useRef } from "react";
import { Download } from "lucide-react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { ApiError } from "@/shared/lib/apiClient";
import { errorMessageKey, errorMessageParams } from "@/shared/lib/errors";
import { Button } from "@/shared/components/ui/button";
import { ErrorState } from "@/shared/components/common/ErrorState";
import { Skeleton } from "@/shared/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import { useDocumentFile } from "../hooks/queries/useDocumentFile";
import { useDownloadDocument } from "../hooks/mutations/useDownloadDocument";
import type { LibraryDocument } from "../types/Document";

interface DocumentViewerDialogProps {
  /** El documento que se ve; `null` cierra el visor. */
  document: LibraryDocument | null;
  onClose: () => void;
}

/**
 * Visor de un PDF dentro de la aplicación (RF-90). El fichero llega como blob con
 * la sesión y se muestra con una URL `blob:` que se libera al cerrar (ficheros §4).
 * El servidor nunca lo renderiza: lo pinta el visor de PDF del navegador.
 */
export function DocumentViewerDialog({ document, onClose }: DocumentViewerDialogProps) {
  const { t } = useTranslation();
  const file = useDocumentFile(document?.id ?? null);
  const download = useDownloadDocument();

  const notFound = file.error instanceof ApiError && file.error.status === 404;

  return (
    <Dialog open={document !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="flex h-[calc(100dvh-2rem)] flex-col sm:max-w-4xl">
        <DialogHeader className="pr-8">
          <DialogTitle className="truncate">{document?.name}</DialogTitle>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <DialogDescription>{document && t(`documents.kinds.${document.kind}`)}</DialogDescription>
            {document && (
              <Button
                variant="outline"
                size="sm"
                disabled={download.isPending}
                onClick={() =>
                  download.mutate(document, {
                    onError: (error) =>
                      toast.error(t(errorMessageKey(error), errorMessageParams(error))),
                  })
                }
              >
                <Download />
                {t("documents.download")}
              </Button>
            )}
          </div>
        </DialogHeader>
        <div className="min-h-0 flex-1">
          {file.isLoading && <Skeleton className="size-full" />}
          {file.isError && (
            <ErrorState
              titleKey={notFound ? "documents.viewer.notFound" : undefined}
              onRetry={notFound ? undefined : () => file.refetch()}
              retrying={file.isFetching}
            />
          )}
          {file.data && (
            <PdfFrame
              blob={file.data}
              title={t("documents.viewer.frameTitle", { name: document?.name })}
            />
          )}
        </div>
        <p className="text-xs text-muted-foreground">{t("documents.viewer.fallback")}</p>
      </DialogContent>
    </Dialog>
  );
}

/**
 * El PDF en un `iframe` con una URL `blob:` creada y liberada en el mismo efecto.
 * Se asigna al `iframe` directamente y no se guarda en el estado: con el doble
 * montaje de `StrictMode`, una URL en estado se liberaría en la primera limpieza y
 * el visor se quedaría con una URL ya muerta.
 */
function PdfFrame({ blob, title }: { blob: Blob; title: string }) {
  const frame = useRef<HTMLIFrameElement>(null);
  useEffect(() => {
    const url = URL.createObjectURL(blob);
    if (frame.current) frame.current.src = url;
    return () => URL.revokeObjectURL(url);
  }, [blob]);
  return <iframe ref={frame} title={title} className="size-full rounded-md border bg-muted" />;
}
