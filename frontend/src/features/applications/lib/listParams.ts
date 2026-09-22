import {
  APPLICATION_SOURCES,
  APPLICATION_STATUSES,
  WORK_MODES,
  type ApplicationListParams,
  type ApplicationSort,
  type ArchivedFilter,
} from "../types/Application";

export const PAGE_SIZE = 20;

export const DEFAULT_LIST_PARAMS: ApplicationListParams = {
  page: 1,
  limit: PAGE_SIZE,
  status: [],
  work_mode: [],
  source: [],
  company_id: null,
  applied_from: null,
  applied_to: null,
  q: "",
  archived: "active",
  sort_by: "applied_at",
  order: "desc",
};

const SORTS: readonly ApplicationSort[] = [
  "applied_at",
  "created_at",
  "updated_at",
  "company",
  "position_title",
];
const ARCHIVED: readonly ArchivedFilter[] = ["active", "archived", "all"];
const DATE_ONLY = /^\d{4}-\d{2}-\d{2}$/;

function oneOf<T extends string>(value: string | null, allowed: readonly T[], fallback: T): T {
  return allowed.includes(value as T) ? (value as T) : fallback;
}

function manyOf<T extends string>(values: string[], allowed: readonly T[]): T[] {
  return values.filter((value): value is T => allowed.includes(value as T));
}

/**
 * URL → filtros del listado. La URL la puede escribir cualquiera (enlace compartido,
 * marcador antiguo): los valores desconocidos se descartan en vez de romper la página
 * o llegar a la API como un 422.
 */
export function parseListParams(search: URLSearchParams): ApplicationListParams {
  const date = (key: string) => {
    const value = search.get(key);
    return value && DATE_ONLY.test(value) ? value : null;
  };

  return {
    ...DEFAULT_LIST_PARAMS,
    page: Math.max(1, Math.floor(Number(search.get("page"))) || 1),
    status: manyOf(search.getAll("status"), APPLICATION_STATUSES),
    work_mode: manyOf(search.getAll("work_mode"), WORK_MODES),
    source: manyOf(search.getAll("source"), APPLICATION_SOURCES),
    company_id: search.get("company_id"),
    applied_from: date("applied_from"),
    applied_to: date("applied_to"),
    q: search.get("q") ?? "",
    archived: oneOf(search.get("archived"), ARCHIVED, DEFAULT_LIST_PARAMS.archived),
    sort_by: oneOf(search.get("sort_by"), SORTS, DEFAULT_LIST_PARAMS.sort_by),
    order: oneOf(search.get("order"), ["asc", "desc"] as const, DEFAULT_LIST_PARAMS.order),
  };
}

/**
 * Filtros → URL. Solo se escriben los valores distintos del por defecto, para que
 * la URL de la vista normal sea simplemente /applications.
 */
export function serializeListParams(params: ApplicationListParams): URLSearchParams {
  const search = new URLSearchParams();
  const defaults = DEFAULT_LIST_PARAMS;

  if (params.q) search.set("q", params.q);
  params.status.forEach((value) => search.append("status", value));
  params.work_mode.forEach((value) => search.append("work_mode", value));
  params.source.forEach((value) => search.append("source", value));
  if (params.company_id) search.set("company_id", params.company_id);
  if (params.applied_from) search.set("applied_from", params.applied_from);
  if (params.applied_to) search.set("applied_to", params.applied_to);
  if (params.archived !== defaults.archived) search.set("archived", params.archived);
  if (params.sort_by !== defaults.sort_by) search.set("sort_by", params.sort_by);
  if (params.order !== defaults.order) search.set("order", params.order);
  if (params.page > 1) search.set("page", String(params.page));

  return search;
}

/** Aplica un cambio de filtros: cualquier cambio que no sea de página vuelve a la 1. */
export function updateListParams(
  current: ApplicationListParams,
  changes: Partial<ApplicationListParams>,
): ApplicationListParams {
  const onlyPage = Object.keys(changes).every((key) => key === "page");
  return { ...current, ...changes, page: onlyPage ? (changes.page ?? current.page) : 1 };
}

export function hasActiveFilters(params: ApplicationListParams): boolean {
  return (
    !!params.q ||
    params.status.length > 0 ||
    params.work_mode.length > 0 ||
    params.source.length > 0 ||
    !!params.company_id ||
    !!params.applied_from ||
    !!params.applied_to ||
    params.archived !== DEFAULT_LIST_PARAMS.archived
  );
}
