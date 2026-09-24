import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import i18n from "@/shared/i18n/i18n";
import { ApiError } from "@/shared/lib/apiClient";
import { ApplicationLoadError } from "./ApplicationLoadError";

function renderWith(error: Error | null, retrying = false) {
  const onRetry = vi.fn();
  render(
    <MemoryRouter>
      <ApplicationLoadError error={error} onRetry={onRetry} retrying={retrying} />
    </MemoryRouter>,
  );
  return { onRetry };
}

describe("ApplicationLoadError", () => {
  afterEach(cleanup);

  beforeAll(async () => {
    await i18n.changeLanguage("es");
  });

  it("offers going back to the list, not retrying, when the application is not found (404)", () => {
    renderWith(new ApiError(404, "Not found", "not_found"));

    expect(screen.getByText(i18n.t("applications.notFound"))).toBeInTheDocument();
    expect(screen.getByRole("link", { name: i18n.t("applications.backToList") })).toHaveAttribute(
      "href",
      "/applications",
    );
    expect(screen.queryByRole("button", { name: i18n.t("common.retry") })).not.toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it.each([
    ["a server error", new ApiError(500, "Internal server error")],
    ["a network error", new TypeError("Failed to fetch")],
    ["no error object", null],
  ])("shows a retryable error alert for %s", async (_label, error) => {
    const { onRetry } = renderWith(error);

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.queryByText(i18n.t("applications.notFound"))).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: i18n.t("common.retry") }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("disables retrying while the refetch is in flight", () => {
    renderWith(new ApiError(503, "Unavailable"), true);

    expect(screen.getByRole("button", { name: i18n.t("common.retry") })).toBeDisabled();
  });
});
