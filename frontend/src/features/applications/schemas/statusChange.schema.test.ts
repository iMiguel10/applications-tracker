import { describe, expect, it } from "vitest";
import { statusChangeSchema } from "./statusChange.schema";

describe("statusChangeSchema", () => {
  it("accepts a status with no date and no note", () => {
    const result = statusChangeSchema.safeParse({
      to_status: "screening",
      changed_at: null,
      note: "",
    });

    expect(result.success).toBe(true);
  });

  it("rejects an empty status", () => {
    const result = statusChangeSchema.safeParse({
      to_status: "",
      changed_at: null,
      note: "",
    });

    expect(result.success).toBe(false);
  });

  it("rejects a note over 5000 characters", () => {
    const result = statusChangeSchema.safeParse({
      to_status: "screening",
      changed_at: null,
      note: "x".repeat(5001),
    });

    expect(result.success).toBe(false);
  });
});
