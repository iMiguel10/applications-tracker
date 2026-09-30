import { useMemo, type ComponentProps, type ReactNode } from "react";
import { Accessibility, type Draggable } from "@dnd-kit/dom";
import { DragDropProvider } from "@dnd-kit/react";
import { isSortable, useSortable } from "@dnd-kit/react/sortable";
import { GripVertical } from "lucide-react";
import { useTranslation } from "react-i18next";

import { cn } from "@/shared/lib/utils";

type SortableItem = { id: string; label: string };
type Plugins = NonNullable<ComponentProps<typeof DragDropProvider>["plugins"]>;
// `@dnd-kit/dom` no exporta el tipo de las opciones del plugin por su nombre.
type AccessibilityOptions = NonNullable<ConstructorParameters<typeof Accessibility>[1]>;

type Props<T extends SortableItem> = {
  items: T[];
  /** El elemento que estaba en `from` pasa a `to` (índices del array). */
  onMove: (from: number, to: number) => void;
  renderItem: (item: T, handle: ReactNode) => ReactNode;
  className?: string;
  itemClassName?: string;
};

/**
 * Lista reordenable arrastrando, con ratón, dedo o teclado (Espacio para coger,
 * flechas para mover, Espacio para soltar, Escape para cancelar).
 *
 * Los anuncios para lectores de pantalla de `@dnd-kit` dicen el id del elemento
 * (un UUID) y en inglés: aquí se sustituyen por el nombre del elemento, en el
 * idioma de la interfaz. El orden no cambia en la lista hasta que el padre lo
 * aplica con `onMove`.
 */
export function SortableList<T extends SortableItem>({
  items,
  onMove,
  renderItem,
  className,
  itemClassName,
}: Props<T>) {
  const { t } = useTranslation();

  // Cada fila lleva su nombre y el total en el `data` del sortable: los anuncios
  // lo leen de ahí y los plugins no dependen de la lista (no se reconfiguran en
  // cada render del padre).
  const plugins = useMemo<Plugins>(() => {
    const describe = (source: Draggable | null) => {
      if (!isSortable(source)) return null;
      const data = source.data as RowData | undefined;
      return {
        label: data?.label ?? "",
        position: source.index + 1,
        total: data?.total ?? 0,
      };
    };
    const options: AccessibilityOptions = {
      screenReaderInstructions: { draggable: t("sortable.instructions") },
      announcements: {
        dragstart: ({ operation: { source } }) => {
          const row = describe(source);
          return row ? t("sortable.picked", row) : undefined;
        },
        dragover: ({ operation: { source } }) => {
          const row = describe(source);
          return row ? t("sortable.moved", row) : undefined;
        },
        dragend: ({ operation: { source }, canceled }) => {
          const row = describe(source);
          if (!row) return undefined;
          return t(canceled ? "sortable.canceled" : "sortable.dropped", row);
        },
      },
    };
    const accessibility = Accessibility.configure(options);
    return (defaults) =>
      defaults.map((plugin) => (plugin === Accessibility ? accessibility : plugin));
  }, [t]);

  return (
    <DragDropProvider
      plugins={plugins}
      onDragEnd={(event) => {
        if (event.canceled) return;
        const { source } = event.operation;
        if (source && isSortable(source) && source.initialIndex !== source.index) {
          onMove(source.initialIndex, source.index);
        }
      }}
    >
      <ul className={className}>
        {items.map((item, index) => (
          <SortableRow
            key={item.id}
            item={item}
            index={index}
            total={items.length}
            className={itemClassName}
          >
            {(handle) => renderItem(item, handle)}
          </SortableRow>
        ))}
      </ul>
    </DragDropProvider>
  );
}

type RowData = { label: string; total: number };

function SortableRow<T extends SortableItem>({
  item,
  index,
  total,
  className,
  children,
}: {
  item: T;
  index: number;
  total: number;
  className?: string;
  children: (handle: ReactNode) => ReactNode;
}) {
  const { t } = useTranslation();
  const data: RowData = { label: item.label, total };
  const { ref, handleRef, isDragSource } = useSortable({ id: item.id, index, data });

  const handle = (
    <button
      ref={handleRef}
      type="button"
      aria-label={t("sortable.handle", { label: item.label })}
      aria-roledescription={t("sortable.roleDescription")}
      className="flex size-8 shrink-0 cursor-grab touch-none items-center justify-center rounded-md text-muted-foreground hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring active:cursor-grabbing"
    >
      <GripVertical className="size-4" aria-hidden />
    </button>
  );

  return (
    <li ref={ref} className={cn(className, isDragSource && "opacity-60")}>
      {children(handle)}
    </li>
  );
}
