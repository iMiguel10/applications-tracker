import { useMemo, useState, type ComponentProps } from "react";
import { Accessibility, type Draggable, type Droppable } from "@dnd-kit/dom";
import {
  DragDropProvider,
  useDragOperation,
  useDraggable,
  useDroppable,
} from "@dnd-kit/react";
import {
  ArrowRightLeft,
  ChevronsLeftRight,
  ChevronsRightLeft,
  GripVertical,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { toast } from "sonner";

import { errorMessageKey, errorMessageParams } from "@/shared/lib/errors";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/shared/components/ui/dropdown-menu";
import { ApplicationStatusBadge } from "@/features/applications/components/ApplicationStatusBadge";
import { ChangeStatusDialog } from "@/features/applications/components/ChangeStatusDialog";
import { useUndoLastStatusChange } from "@/features/applications/hooks/mutations/useUndoLastStatusChange";
import type { ApplicationStatus } from "@/features/applications/types/Application";
import { useMoveCard } from "../hooks/mutations/useMoveCard";
import { useCollapsedColumns } from "../hooks/useCollapsedColumns";
import { canMove, daysInStatus } from "../lib/board";
import type { BoardFilters } from "../services/board.service";
import type { Board, BoardCard, BoardColumn } from "../types/Board";

type Plugins = NonNullable<ComponentProps<typeof DragDropProvider>["plugins"]>;
// `@dnd-kit/dom` no exporta el tipo de las opciones del plugin por su nombre.
type AccessibilityOptions = NonNullable<
  ConstructorParameters<typeof Accessibility>[1]
>;

const UNDO_TOAST_MS = 10_000;

/** Lo que lleva cada tarjeta para los anuncios y para saber dónde puede caer. */
type CardData = {
  label: string;
  status: ApplicationStatus;
  allowed: ApplicationStatus[];
};
type ColumnData = { label: string };

/** La tarjeta del "Mover a…" abierto y el estado que se eligió en el menú. */
type MoveTarget = {
  id: string;
  allowed: ApplicationStatus[];
  to: ApplicationStatus;
};
type OnMoveTo = (target: MoveTarget) => void;

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
 *
 * Sin arrastrar (RF-123), el menú "Mover a…" de cada tarjeta abre el diálogo de
 * cambio de estado con el destino ya elegido, con nota y fecha. Las columnas de
 * los estados finales se pueden plegar (RF-122) y siguen aceptando tarjetas.
 */
export function ApplicationBoard({
  board,
  filters,
  listHref,
}: ApplicationBoardProps) {
  const { t } = useTranslation();
  const move = useMoveCard(filters);
  const undo = useUndoLastStatusChange();
  const collapsed = useCollapsedColumns();
  // El destino se guarda aparte de `open` para que el diálogo no se vacíe
  // mientras se cierra.
  const [moveTarget, setMoveTarget] = useState<MoveTarget | null>(null);
  const [moveOpen, setMoveOpen] = useState(false);
  const onMoveTo: OnMoveTo = (target) => {
    setMoveTarget(target);
    setMoveOpen(true);
  };
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
              collapsed={collapsed.isCollapsed(column.status)}
              onToggle={() => collapsed.toggle(column.status)}
              onMoveTo={onMoveTo}
            />
          ))}
        </ul>
      </div>
      <ChangeStatusDialog
        application={{
          id: moveTarget?.id ?? "",
          allowed_transitions: moveTarget?.allowed ?? [],
        }}
        initialStatus={moveTarget?.to}
        open={moveOpen}
        onOpenChange={setMoveOpen}
      />
    </DragDropProvider>
  );
}

function BoardColumnView({
  column,
  label,
  listHref,
  collapsed,
  onToggle,
  onMoveTo,
}: {
  column: BoardColumn;
  label: string;
  listHref: string;
  collapsed: boolean;
  onToggle: () => void;
  onMoveTo: OnMoveTo;
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
  // Solo se pliegan las de estados finales (RF-122): las tarjetas ya no salen de ahí.
  const collapsible = column.allowed_transitions.length === 0;
  const folded = collapsible && collapsed;
  const toggleLabel = t(folded ? "board.expand" : "board.collapse", {
    column: label,
  });
  const toggle = collapsible && (
    <Button
      variant="ghost"
      size="icon-xs"
      aria-expanded={!folded}
      aria-label={toggleLabel}
      title={toggleLabel}
      onClick={onToggle}
    >
      {folded ? <ChevronsLeftRight /> : <ChevronsRightLeft />}
    </Button>
  );

  return (
    <li
      ref={ref}
      aria-label={t("board.columnLabel", {
        column: label,
        count: column.total,
      })}
      className={cn(
        "flex shrink-0 flex-col gap-2 rounded-xl border bg-muted/40 p-2 transition-colors",
        folded ? "w-12 items-center" : "w-72",
        isDropTarget && "border-primary bg-primary/5",
        unavailable && "opacity-40",
      )}
    >
      {folded ? (
        // Plegada sigue siendo un destino: se puede soltar una tarjeta encima.
        <>
          {toggle}
          <span className="text-sm tabular-nums text-muted-foreground">
            {column.total}
          </span>
          <span className="text-sm font-medium text-muted-foreground [writing-mode:vertical-rl]">
            {label}
          </span>
        </>
      ) : (
        <>
          <div className="flex items-center justify-between gap-2 px-1 pt-1">
            <ApplicationStatusBadge status={column.status} />
            <div className="flex items-center gap-1">
              <span className="text-sm tabular-nums text-muted-foreground">
                {column.total}
              </span>
              {toggle}
            </div>
          </div>
          <ul className="grid min-h-16 gap-2">
            {column.items.map((card) => (
              <BoardCardView
                key={card.id}
                card={card}
                column={column}
                onMoveTo={onMoveTo}
              />
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
        </>
      )}
    </li>
  );
}

function BoardCardView({
  card,
  column,
  onMoveTo,
}: {
  card: BoardCard;
  column: BoardColumn;
  onMoveTo: OnMoveTo;
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
      {column.allowed_transitions.length > 0 && (
        <DropdownMenu>
          <DropdownMenuTrigger
            render={
              <Button
                variant="ghost"
                size="icon-sm"
                className="shrink-0 text-muted-foreground"
                aria-label={t("board.moveTo", { label })}
                title={t("board.moveToTitle")}
              />
            }
          >
            <ArrowRightLeft />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuGroup>
              <DropdownMenuLabel>{t("board.moveToTitle")}</DropdownMenuLabel>
              {column.allowed_transitions.map((status) => (
                <DropdownMenuItem
                  key={status}
                  onClick={() =>
                    onMoveTo({
                      id: card.id,
                      allowed: column.allowed_transitions,
                      to: status,
                    })
                  }
                >
                  {t(`applications.status.${status}`)}
                </DropdownMenuItem>
              ))}
            </DropdownMenuGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      )}
    </li>
  );
}
