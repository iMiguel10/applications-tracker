import { describe, expect, it } from "vitest";

import type { LimitUsage } from "../types/Usage";
import { usageValues } from "./values";

const base = { key: "storage_bytes", renews: false } as const;

describe("usageValues", () => {
  it("formatea los bytes y no pasa count", () => {
    const item: LimitUsage = {
      ...base,
      unit: "bytes",
      used: 1024 * 1024,
      limit: 100 * 1024 * 1024,
      remaining: 99 * 1024 * 1024,
    };
    expect(usageValues(item, "es")).toEqual({ used: "1 MB", limit: "100 MB", remaining: "99 MB" });
  });

  it("deja los elementos como números, con count para el plural", () => {
    const item: LimitUsage = {
      key: "documents",
      renews: false,
      unit: "count",
      used: 3,
      limit: 100,
      remaining: 97,
    };
    expect(usageValues(item, "es")).toEqual({ used: 3, limit: 100, remaining: 97, count: 97 });
  });
});
