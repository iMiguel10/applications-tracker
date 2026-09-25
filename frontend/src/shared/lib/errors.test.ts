import { beforeAll, describe, expect, it } from "vitest";

import i18n from "@/shared/i18n/i18n";
import { ApiError } from "./apiClient";
import { errorMessageKey, errorMessageParams } from "./errors";

describe("error messages", () => {
  beforeAll(async () => {
    await i18n.changeLanguage("es");
  });

  it("say which limit was reached and how much (RF-142)", () => {
    const error = new ApiError(409, "Limit reached", "applications_limit_reached", {
      limit: 5000,
      used: 5000,
    });

    expect(i18n.t(errorMessageKey(error), errorMessageParams(error))).toBe(
      "Has alcanzado tu límite de 5000 solicitudes",
    );
  });

  it("have no params for errors without extra data", () => {
    expect(errorMessageParams(new Error("x"))).toEqual({});
    expect(errorMessageParams(new ApiError(404, "Not found", "not_found"))).toEqual({});
  });
});
