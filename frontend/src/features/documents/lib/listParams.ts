import { DOCUMENT_KINDS, type DocumentKindFilter, type DocumentListParams } from "../types/Document";

export const PAGE_SIZE = 20;

export const DEFAULT_LIST_PARAMS: DocumentListParams = {
  page: 1,
  limit: PAGE_SIZE,
  kind: "all",
  archived: false,
};

const KINDS: readonly DocumentKindFilter[] = ["all", ...DOCUMENT_KINDS];

/** URL → filtros de la biblioteca (decisión A16): un valor desconocido se descarta. */
export function parseListParams(search: URLSearchParams): DocumentListParams {
  const kind = search.get("kind") as DocumentKindFilter | null;
  return {
    ...DEFAULT_LIST_PARAMS,
    page: Math.max(1, Math.floor(Number(search.get("page"))) || 1),
    kind: kind && KINDS.includes(kind) ? kind : DEFAULT_LIST_PARAMS.kind,
    archived: search.get("archived") === "true",
  };
}

export function serializeListParams(params: DocumentListParams): URLSearchParams {
  const search = new URLSearchParams();
  if (params.kind !== DEFAULT_LIST_PARAMS.kind) search.set("kind", params.kind);
  if (params.archived) search.set("archived", "true");
  if (params.page > 1) search.set("page", String(params.page));
  return search;
}

/** Cualquier cambio que no sea de página vuelve a la 1. */
export function updateListParams(
  current: DocumentListParams,
  changes: Partial<DocumentListParams>,
): DocumentListParams {
  const onlyPage = Object.keys(changes).every((key) => key === "page");
  return { ...current, ...changes, page: onlyPage ? (changes.page ?? current.page) : 1 };
}
