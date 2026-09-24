import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/shared/lib/utils";
import { Card, CardContent } from "@/shared/components/ui/card";
import { Skeleton } from "@/shared/components/ui/skeleton";

// Los esqueletos van siempre sobre `bg-card`: `--muted` y `--background` son el mismo
// tono en claro, así que sobre el fondo de página no se verían.

/** Anuncia la carga a lectores de pantalla; el esqueleto en sí es decorativo. */
function LoadingRegion({ className, children }: { className?: string; children: ReactNode }) {
  const { t } = useTranslation();
  return (
    <div role="status" aria-live="polite">
      <span className="sr-only">{t("common.loading")}</span>
      <div aria-hidden className={className}>
        {children}
      </div>
    </div>
  );
}

function Bar({ className }: { className?: string }) {
  return <Skeleton className={cn("h-4 motion-reduce:animate-none", className)} />;
}

/** Tabla de un listado mientras llega: mismas filas y columnas aproximadas. */
export function TableSkeleton({ rows = 6, columns = 4 }: { rows?: number; columns?: number }) {
  return (
    <LoadingRegion>
      <Card className="py-0">
        <CardContent className="divide-y px-0">
          {Array.from({ length: rows }, (_, row) => (
            <div key={row} className="flex items-center gap-6 px-4 py-3.5">
              {Array.from({ length: columns }, (_, column) => (
                <Bar
                  key={column}
                  className={column === 0 ? "w-1/4" : column === columns - 1 ? "ml-auto w-16" : "w-1/6"}
                />
              ))}
            </div>
          ))}
        </CardContent>
      </Card>
    </LoadingRegion>
  );
}

/** Filas de una sección (entrevistas, recordatorios…). */
export function ListSkeleton({ rows = 2 }: { rows?: number }) {
  return (
    <LoadingRegion className="grid gap-2">
      {Array.from({ length: rows }, (_, row) => (
        <div key={row} className="grid gap-2 rounded-lg border bg-card p-3">
          <Bar className="w-1/3" />
          <Bar className="h-3 w-1/2" />
        </div>
      ))}
    </LoadingRegion>
  );
}

/** Tarjetas del dashboard: la misma rejilla que la página real. */
export function DashboardSkeleton() {
  const card = (key: number, tall: boolean) => (
    <Card key={key}>
      <CardContent className="grid gap-4">
        <Bar className="w-1/3" />
        <Skeleton className={cn("w-full motion-reduce:animate-none", tall ? "h-52" : "h-16")} />
      </CardContent>
    </Card>
  );

  return (
    <LoadingRegion className="grid gap-6">
      <div className="grid gap-4 lg:grid-cols-[2fr_2fr_1fr]">
        {[0, 1, 2].map((key) => card(key, true))}
      </div>
      <div className="grid gap-4 lg:grid-cols-3">{[3, 4, 5].map((key) => card(key, false))}</div>
    </LoadingRegion>
  );
}

/** Detalle de una solicitud: cabecera, tarjeta de campos y columna de secciones. */
export function DetailSkeleton() {
  return (
    <LoadingRegion className="grid gap-6">
      <div className="grid gap-2">
        <Skeleton className="h-4 w-24 bg-card motion-reduce:animate-none" />
        <Skeleton className="h-8 w-72 bg-card motion-reduce:animate-none" />
        <Skeleton className="h-5 w-20 rounded-full bg-card motion-reduce:animate-none" />
      </div>
      <div className="grid items-start gap-6 lg:grid-cols-[3fr_2fr]">
        <Card>
          <CardContent className="grid gap-5 sm:grid-cols-2">
            {Array.from({ length: 6 }, (_, index) => (
              <div key={index} className="grid gap-2">
                <Bar className="h-3 w-20" />
                <Bar className="w-32" />
              </div>
            ))}
          </CardContent>
        </Card>
        <ListSkeleton rows={3} />
      </div>
    </LoadingRegion>
  );
}
