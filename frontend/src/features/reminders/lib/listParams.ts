import type { ReminderListParams, ReminderStatusFilter } from "../types/Reminder";

export const PAGE_SIZE = 20;

export const DEFAULT_LIST_PARAMS: ReminderListParams = {
  page: 1,
  limit: PAGE_SIZE,
  status: "pending",
  sort_by: "due_at",
  order: "asc",
};

const STATUSES: readonly ReminderStatusFilter[] = ["pending", "done", "dismissed", "all"];

function oneOf<T extends string>(value: string | null, allowed: readonly T[], fallback: T): T {
  return allowed.includes(value as T) ? (value as T) : fallback;
}

/**
 * URL → filtros del listado (decisión A16, igual que las solicitudes): un valor
 * desconocido se descarta en vez de llegar a la API como un 422.
 */
export function parseListParams(search: URLSearchParams): ReminderListParams {
  return {
    ...DEFAULT_LIST_PARAMS,
    page: Math.max(1, Math.floor(Number(search.get("page"))) || 1),
    status: oneOf(search.get("status"), STATUSES, DEFAULT_LIST_PARAMS.status),
  };
}

export function serializeListParams(params: ReminderListParams): URLSearchParams {
  const search = new URLSearchParams();
  if (params.status !== DEFAULT_LIST_PARAMS.status) search.set("status", params.status);
  if (params.page > 1) search.set("page", String(params.page));
  return search;
}

/** Aplica un cambio de filtros: cualquier cambio que no sea de página vuelve a la 1. */
export function updateListParams(
  current: ReminderListParams,
  changes: Partial<ReminderListParams>,
): ReminderListParams {
  const onlyPage = Object.keys(changes).every((key) => key === "page");
  return { ...current, ...changes, page: onlyPage ? (changes.page ?? current.page) : 1 };
}
