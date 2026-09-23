import { describe, expect, it } from "vitest";
import { DEFAULT_LIST_PARAMS, parseListParams, serializeListParams, updateListParams } from "./listParams";

describe("parseListParams", () => {
  it("returns the defaults for an empty URL", () => {
    expect(parseListParams(new URLSearchParams())).toEqual(DEFAULT_LIST_PARAMS);
  });

  it("drops a status it does not know instead of sending it to the API", () => {
    expect(parseListParams(new URLSearchParams("status=snoozed")).status).toBe("pending");
  });

  it("clamps an invalid page to 1", () => {
    expect(parseListParams(new URLSearchParams("page=-3")).page).toBe(1);
  });
});

describe("serializeListParams", () => {
  it("writes nothing for the default view", () => {
    expect(serializeListParams(DEFAULT_LIST_PARAMS).toString()).toBe("");
  });

  it("round-trips through the URL", () => {
    const params = { ...DEFAULT_LIST_PARAMS, status: "done" as const, page: 3 };

    expect(parseListParams(serializeListParams(params))).toEqual(params);
  });
});

describe("updateListParams", () => {
  it("goes back to page 1 when a filter changes", () => {
    const current = { ...DEFAULT_LIST_PARAMS, page: 4 };

    expect(updateListParams(current, { status: "all" }).page).toBe(1);
  });

  it("keeps the filters when only the page changes", () => {
    const current = { ...DEFAULT_LIST_PARAMS, status: "done" as const };

    expect(updateListParams(current, { page: 2 })).toEqual({ ...current, page: 2 });
  });
});
