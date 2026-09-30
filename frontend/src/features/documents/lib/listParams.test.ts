import { describe, expect, it } from "vitest";

import {
  DEFAULT_LIST_PARAMS,
  parseListParams,
  serializeListParams,
  updateListParams,
} from "./listParams";

describe("listParams de la biblioteca", () => {
  it("lee el tipo y la página de la URL y descarta lo desconocido", () => {
    expect(parseListParams(new URLSearchParams("kind=cover_letter&page=3"))).toEqual({
      ...DEFAULT_LIST_PARAMS,
      kind: "cover_letter",
      page: 3,
    });
    expect(parseListParams(new URLSearchParams("kind=foto&page=-2"))).toEqual(DEFAULT_LIST_PARAMS);
  });

  it("no escribe en la URL los valores por defecto", () => {
    expect(serializeListParams(DEFAULT_LIST_PARAMS).toString()).toBe("");
    expect(serializeListParams({ ...DEFAULT_LIST_PARAMS, kind: "cv", page: 2 }).toString()).toBe(
      "kind=cv&page=2",
    );
  });

  it("vuelve a la página 1 al cambiar el filtro", () => {
    expect(updateListParams({ ...DEFAULT_LIST_PARAMS, page: 4 }, { kind: "cv" }).page).toBe(1);
    expect(updateListParams(DEFAULT_LIST_PARAMS, { page: 2 }).page).toBe(2);
  });
});
