import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { toast } from "sonner";

import i18n from "@/shared/i18n/i18n";
import { ApiError } from "@/shared/lib/apiClient";
import { downloadBlob } from "@/shared/lib/download";
import { authService } from "../services/auth.service";
import { ExportDataCard } from "./ExportDataCard";

vi.mock("../services/auth.service", () => ({
  authService: { exportData: vi.fn() },
}));
vi.mock("@/shared/lib/download", () => ({ downloadBlob: vi.fn() }));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

function renderCard() {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <ExportDataCard />
    </QueryClientProvider>,
  );
}

beforeAll(async () => {
  await i18n.changeLanguage("es");
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ExportDataCard (issue #4)", () => {
  it("descarga el .zip con la fecha en el nombre", async () => {
    const blob = new Blob(["PK"], { type: "application/zip" });
    vi.mocked(authService.exportData).mockResolvedValue(blob);
    renderCard();

    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: i18n.t("account.export.button") }));

    await waitFor(() => expect(downloadBlob).toHaveBeenCalled());
    const [downloaded, filename] = vi.mocked(downloadBlob).mock.calls[0];
    expect(downloaded).toBe(blob);
    expect(filename).toMatch(/^applications-tracker-export-\d{4}-\d{2}-\d{2}\.zip$/);
  });

  it("mientras se prepara, el botón lo dice y no se puede volver a pulsar", async () => {
    vi.mocked(authService.exportData).mockReturnValue(new Promise(() => {}));
    renderCard();

    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: i18n.t("account.export.button") }));

    expect(
      await screen.findByRole("button", { name: i18n.t("account.export.preparing") }),
    ).toBeDisabled();
  });

  it("si se pasa del límite, lo explica", async () => {
    vi.mocked(authService.exportData).mockRejectedValue(
      new ApiError(429, "Too many requests", "rate_limited"),
    );
    renderCard();

    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: i18n.t("account.export.button") }));

    await waitFor(() => expect(toast.error).toHaveBeenCalled());
    expect(downloadBlob).not.toHaveBeenCalled();
  });

  it("enlaza su página del manual", () => {
    renderCard();

    const help = screen.getByRole("link", {
      name: `${i18n.t("help.pages.exportData")} ${i18n.t("help.newTab")}`,
    });
    expect(help.getAttribute("href")).toMatch(/\/uso\/exportar$/);
  });
});
