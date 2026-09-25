import { describe, expect, it } from "vitest";

import { usageLevel } from "./level";

const item = (used: number, limit: number | null) => ({
  key: "applications" as const,
  used,
  limit,
  remaining: limit === null ? null : Math.max(limit - used, 0),
  renews: false,
});

describe("usageLevel", () => {
  it.each([
    [0, 100, "ok"],
    [79, 100, "ok"],
    [80, 100, "warning"],
    [99, 100, "warning"],
    [100, 100, "reached"],
    // Un límite rebajado por debajo de lo ya creado.
    [120, 100, "reached"],
    [0, 0, "reached"],
    // Excepción "sin límite": nunca avisa, por mucho que lleve.
    [1_000_000, null, "unlimited"],
  ] as const)("%i of %i is %s", (used, limit, expected) => {
    expect(usageLevel(item(used, limit), 0.8)).toBe(expected);
  });
});
