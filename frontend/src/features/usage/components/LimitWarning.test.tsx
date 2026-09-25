import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import i18n from "@/shared/i18n/i18n";
import { usageService } from "../services/usage.service";
import { LimitWarning } from "./LimitWarning";

vi.mock("../services/usage.service", () => ({ usageService: { get: vi.fn() } }));

function renderWith(used: number, limit: number) {
  vi.mocked(usageService.get).mockResolvedValue({
    warning_ratio: 0.8,
    limits: [
      { key: "companies", used, limit, remaining: Math.max(limit - used, 0), renews: false },
    ],
  });
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <LimitWarning limitKey="companies" />
    </QueryClientProvider>,
  );
}

describe("LimitWarning", () => {
  beforeAll(async () => {
    await i18n.changeLanguage("es");
  });
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("stays silent below the warning threshold", async () => {
    renderWith(1_599, 2_000);

    await vi.waitFor(() => expect(usageService.get).toHaveBeenCalled());
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("says how many are left from 80 % on (RF-144), with localized numbers", async () => {
    renderWith(1_600, 2_000);

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Te quedan 400 de las 2000 empresas de tu cuenta.",
    );
  });

  it("explains how to free up room once the limit is reached", async () => {
    renderWith(2_000, 2_000);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Has alcanzado tu límite de 2000 empresas",
    );
  });

  it("agrees in number when a single one is left", async () => {
    renderWith(4, 5);

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Te queda 1 de las 5 empresas de tu cuenta.",
    );
  });
});
