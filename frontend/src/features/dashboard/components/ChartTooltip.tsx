interface TooltipPayloadEntry<T> {
  payload: T;
}

interface ChartTooltipProps<T> {
  active?: boolean;
  payload?: TooltipPayloadEntry<T>[];
  formatLabel: (row: T) => string;
  formatValue: (row: T) => string;
}

/** Tooltip de recharts con el mismo lenguaje visual que el resto de la app
 * (popover), en vez del recuadro blanco por defecto. */
export function ChartTooltip<T>({ active, payload, formatLabel, formatValue }: ChartTooltipProps<T>) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;

  return (
    <div className="rounded-lg bg-popover p-2.5 text-sm text-popover-foreground shadow-md ring-1 ring-foreground/10">
      <p className="font-medium">{formatLabel(row)}</p>
      <p className="text-muted-foreground">{formatValue(row)}</p>
    </div>
  );
}
