import { differenceInCalendarDays } from "date-fns";
import type { ApplicationStatus } from "@/features/applications/types/Application";
import type { Board, BoardCard } from "../types/Board";

/** Días completos en el estado, contados en días del calendario local (RF-120). */
export function daysInStatus(
  statusSince: string,
  now: Date = new Date(),
): number {
  return Math.max(0, differenceInCalendarDays(now, new Date(statusSince)));
}

/** La columna desde la que se arrastra una tarjeta admite soltarla en `to`. */
export function canMove(
  board: Board,
  from: ApplicationStatus,
  to: ApplicationStatus,
): boolean {
  const column = board.columns.find((item) => item.status === from);
  return from !== to && !!column?.allowed_transitions.includes(to);
}

/**
 * El tablero tras mover una tarjeta, para pintarlo al soltar sin esperar a la
 * API: sale de su columna y entra la primera de la de destino (la que acaba de
 * entrar en el estado), con los totales ajustados. Sin cambios si no se puede.
 */
export function moveCard(
  board: Board,
  cardId: string,
  from: ApplicationStatus,
  to: ApplicationStatus,
  now: Date = new Date(),
): Board {
  const source = board.columns.find((column) => column.status === from);
  const card = source?.items.find((item) => item.id === cardId);
  if (!card || !canMove(board, from, to)) return board;
  const moved: BoardCard = { ...card, status_since: now.toISOString() };
  return {
    columns: board.columns.map((column) => {
      if (column.status === from) {
        return {
          ...column,
          total: column.total - 1,
          items: column.items.filter((item) => item.id !== cardId),
        };
      }
      if (column.status === to) {
        return {
          ...column,
          total: column.total + 1,
          items: [moved, ...column.items],
        };
      }
      return column;
    }),
  };
}
