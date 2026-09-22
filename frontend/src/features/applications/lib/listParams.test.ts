import { describe, expect, it } from "vitest";
import {
  DEFAULT_LIST_PARAMS,
  parseListParams,
  serializeListParams,
  updateListParams,
} from "./listParams";

describe("parseListParams", () => {
  it("returns the defaults for an empty URL", () => {
    expect(parseListParams(new URLSearchParams())).toEqual(DEFAULT_LIST_PARAMS);
  });

  it("reads repeated params as lists", () => {
    const params = parseListParams(new URLSearchParams("status=applied&status=screening"));

    expect(params.status).toEqual(["applied", "screening"]);
  });

  it("drops values it does not know instead of sending them to the API", () => {
    const params = parseListParams(
      new URLSearchParams(
        "status=ghosted&status=offer&sort_by=salary&archived=deleted&page=-3&applied_from=01/09/2026",
      ),
    );

    expect(params.status).toEqual(["offer"]);
    expect(params.sort_by).toBe("applied_at");
    expect(params.archived).toBe("active");
    expect(params.page).toBe(1);
    expect(params.applied_from).toBeNull();
  });
});

describe("serializeListParams", () => {
  it("writes nothing for the default view", () => {
    expect(serializeListParams(DEFAULT_LIST_PARAMS).toString()).toBe("");
  });

  it("round-trips through the URL", () => {
    const params = {
      ...DEFAULT_LIST_PARAMS,
      q: "backend",
      status: ["applied" as const, "offer" as const],
      archived: "all" as const,
      sort_by: "company" as const,
      order: "asc" as const,
      page: 3,
    };

    expect(parseListParams(serializeListParams(params))).toEqual(params);
  });
});

describe("updateListParams", () => {
  it("goes back to page 1 when a filter changes", () => {
    const current = { ...DEFAULT_LIST_PARAMS, page: 4 };

    expect(updateListParams(current, { status: ["offer"] }).page).toBe(1);
  });

  it("keeps the filters when only the page changes", () => {
    const current = { ...DEFAULT_LIST_PARAMS, q: "dev" };

    expect(updateListParams(current, { page: 2 })).toEqual({ ...current, page: 2 });
  });
});
