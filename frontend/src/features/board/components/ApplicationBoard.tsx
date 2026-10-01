import { useMemo, type ComponentProps } from "react";
import { Accessibility, type Draggable, type Droppable } from "@dnd-kit/dom";
import {
  DragDropProvider,
  useDragOperation,
  useDraggable,
  useDroppable,
} from "@dnd-kit/react";
import { GripVertical } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { toast } from "sonner";

import { errorMessageKey, errorMessageParams } from "@/shared/lib/errors";
import { cn } from "@/shared/lib/utils";
import { ApplicationStatusBadge } from "@/features/applications/components/ApplicationStatusBadge";
import { useUndoLastStatusChange } from "@/features/applications/hooks/mutations/useUndoLastStatusChange";
import type { ApplicationStatus } from "@/features/applications/types/Application";
import { useMoveCard } from "../hooks/mutations/useMoveCard";
import { canMove, daysInStatus } from "../lib/board";
import type { BoardFilters } from "../services/board.service";
import type { Board, BoardCard, BoardColumn } from "../types/Board";

type Plugins = NonNullable<ComponentProps<typeof DragDropProvider>["plugins"]>;
// `@dnd-kit/dom` no exporta el tipo de las opciones del plugin por su nombre.
type AccessibilityOptions = NonNullable<
  ConstructorParameters<typeof Accessibility>[1]
>;

/** Lo que lleva cada tarjeta para los anuncios y para saber dónde puede caer. */
const UNDO_TOAST_MS = 10_000;

type CardData ={
  label: string;
  status: ApplicationStatus;
  allowed: ApplicationStatus[];
};
type ColumnData = { label: string };

interface ApplicationBoardProps {
  board: Board;
  filters: BoardFilters;
  /** Enlace al listado filtrado por un estado ("y N más"). */
  listHref: (status: ApplicationStatus) => string;
}

/**
 * El tablero (RF-120, RF-121): una columna por estado. Una tarjeta se arrastra por
 * su asa, con ratón, dedo o teclado (Espacio para coger, flechas, Espacio para
 * soltar), y solo cae en las columnas de sus transiciones permitidas: las demás
 * se atenúan mientras se arrastra. Soltar cambia el estado al momento con fecha
 * "ahora" y ofrece Deshacer (decisión 0014).
 */
export function ApplicationBoard({
  board,
  filters,
  listHref,
}: ApplicationBoardProps) {
  const { t } = useTranslation();
  const move = useMoveCard(filters);
  const undo = useUndoLastStatusChange();
  const statusLabel = (status: ApplicationStatus) =>
    t(`applications.status.${status}`);

  const plugins = useMemo<Plugins>(() => {
    const card = (source: Draggable | null) =>
      source?.data as CardData | undefined;
    const column = (target: Droppable | null) =>
      target?.data as ColumnData | undefined;
    const options: AccessibilityOptions = {
      screenReaderInstructions: { draggable: t("board.dnd.instructions") },
      announcements: {
        dragstart: ({ operation: { source } }) => {
          const data = card(source);
          return data
            ? t("board.dnd.picked", {
                label: data.label,
                column: t(`applications.status.${data.status}`),
              })
            : undefined;
        },
        dragover: ({ operation: { source, target } }) => {
          const data = card(source);
          const over = column(target);
          if (!data) return undefined;
          return over
            ? t("board.dnd.over", { label: data.label, column: over.label })
            : t("board.dnd.outside", { label: data.label });
        },
        dragend: ({ operation: { source, target }, canceled }) => {
          const data = card(source);
          const over = column(target);
          if (!data) return undefined;
          return canceled || !over
            ? t("board.dnd.canceled", { label: data.label })
            : t("board.dnd.dropped", { label: data.label, column: over.label });
        },
      },
    };
    const accessibility = Accessibility.configure(options);
    return (defaults) =>
      defaults.map((plugin) =>
        plugin === Accessibility ? accessibility : plugin,
      );
  }, [t]);

  const onDrop = (
    cardId: string,
    label: string,
    from: ApplicationStatus,
    to: ApplicationStatus,
  ) => {
    if (!canMove(board, from, to)) return;
    move.mutate(
      { cardId, from, to },
      {
        onSuccess: () =>
          toast.success(t("board.moved", { label, column: statusLabel(to) }), {
            // Más que los 4 s por defecto: da tiempo a ver el error y deshacerlo.
            duration: UNDO_TOAST_MS,
            action: {
              label: t("board.undo"),
              onClick: () =>
                undo.mutate(cardId, {
                  onSuccess: () => toast.success(t("board.undone", { label })),
                  onError: (error) =>
                    toast.error(
                      t(errorMessageKey(error), errorMessageParams(error)),
                    ),
                }),
            },
          }),
        onError: (error) =>
          toast.error(t(errorMessageKey(error), errorMessageParams(error))),
      },
    );
  };

  return (
    <DragDropProvider
      plugins={plugins}
      onDragEnd={(event) => {
        if (event.canceled) return;
        const { source, target } = event.operation;
        const data = source?.data as CardData | undefined;
        if (!source || !target || !data) return;
        onDrop(
          String(source.id),
          data.label,
          data.status,
          target.id as ApplicationStatus,
        );
      }}
    >
      {/* Desplazamiento horizontal propio: en pantallas estrechas las columnas no
          caben y la página no debe desbordarse a lo ancho. */}
      <div className="-mx-4 overflow-x-auto px-4 pb-2 sm:mx-0 sm:px-0">
        <ul className="flex min-w-max gap-3" aria-label={t("board.title")}>
          {board.columns.map((column) => (
            <BoardColumnView
              key={column.status}
              column={column}
              label={statusLabel(column.status)}
              listHref={listHref(column.status)}
            />
          ))}
        </ul>
      </div>
    </DragDropProvider>
  );
}

function BoardColumnView({
  column,
  label,
  listHref,
}: {
  column: BoardColumn;
  label: string;
  listHref: string;
}) {
  const { t } = useTranslation();
  const data: ColumnData = { label };
  const { ref, isDropTarget } = useDroppable({
    id: column.status,
    data,
    accept: (source) => {
      const card = source.data as CardData | undefined;
      return !!card && card.allowed.includes(column.status);
    },
  });
  const { source } = useDragOperation();
  const dragged = source?.data as CardData | undefined;
  // Mientras se arrastra, las columnas a las que no puede ir la tarjeta se
  // atenúan (RF-121). La suya no: es de donde sale.
  const unavailable =
    !!dragged &&
    dragged.status !== column.status &&
    !dragged.allowed.includes(column.status);
  const hidden = column.total - column.items.length;

  return (
    <li
      ref={ref}
      aria-label={t("board.columnLabel", {
        column: label,
        count: column.total,
      })}
      className={cn(
        "flex w-72 shrink-0 flex-col gap-2 rounded-xl border bg-muted/40 p-2 transition-colors",
        isDropTarget && "border-primary bg-primary/5",
        unavailable && "opacity-40",
      )}
    >
      <div className="flex items-center justify-between gap-2 px-1 pt-1">
        <ApplicationStatusBadge status={column.status} />
        <span className="text-sm tabular-nums text-muted-foreground">
          {column.total}
        </span>
      </div>
      <ul className="grid min-h-16 gap-2">
        {column.items.map((card) => (
          <BoardCardView key={card.id} card={card} column={column} />
        ))}
      </ul>
      {hidden > 0 && (
        <Link
          to={listHref}
          className="px-1 pb-1 text-sm text-muted-foreground underline-offset-2 hover:underline"
        >
          {t("board.more", { count: hidden })}
        </Link>
      )}
    </li>
  );
}

function BoardCardView({
  card,
  column,
}: {
  card: BoardCard;
  column: BoardColumn;
}) {
  const { t } = useTranslation();
  const label = `${card.position_title} · ${card.company.name}`;
  const data: CardData = {
    label,
    status: column.status,
    allowed: column.allowed_transitions,
  };
  const { ref, handleRef, isDragSource } = useDraggable({
    id: card.id,
    data,
    // Un estado final no tiene a dónde ir: la tarjeta no se arrastra.
    disabled: column.allowed_transitions.length === 0,
  });
  const days = daysInStatus(card.status_since);

  return (
    <li
      ref={ref}
      className={cn(
        "flex items-start gap-1 rounded-lg border bg-card p-2 shadow-xs",
        isDragSource && "opacity-60",
      )}
    >
      {column.allowed_transitions.length > 0 && (
        <button
          ref={handleRef}
          type="button"
          aria-label={t("board.dnd.handle", { label })}
          aria-roledescription={t("sortable.roleDescription")}
          className="flex size-7 shrink-0 cursor-grab touch-none items-center justify-center rounded-md text-muted-foreground hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring active:cursor-grabbing"
        >
          <GripVertical className="size-4" aria-hidden />
        </button>
      )}
      <div className="grid min-w-0 flex-1 gap-0.5 p-0.5">
        <Link
          to={`/applications/${card.id}`}
          className="truncate font-medium underline-offset-2 hover:underline"
          title={card.position_title}
        >
          {card.position_title}
        </Link>
        <span
          className="truncate text-sm text-muted-foreground"
          title={card.company.name}
        >
          {card.company.name}
        </span>
        <span className="text-xs text-muted-foreground">
          {days === 0
            ? t("board.sinceToday")
            : t("board.days", { count: days })}
        </span>
      </div>
    </li>
  );
}
