import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import i18n from "@/shared/i18n/i18n";
import { ApiError } from "@/shared/lib/apiClient";
import { unsubscribeService } from "@/features/notifications/services/unsubscribe.service";
import { UnsubscribePage } from "./UnsubscribePage";

// El diseño de las pantallas de acceso (tema, panel de marca) no es lo que se prueba.
vi.mock("@/shared/components/layout/AuthLayout", () => ({
  AuthLayout: ({
    children,
    footer,
  }: {
    children: ReactNode;
    footer: ReactNode;
  }) => (
    <main>
      {children}
      {footer}
    </main>
  ),
}));
vi.mock("@/features/notifications/services/unsubscribe.service", () => ({
  unsubscribeService: { describe: vi.fn(), confirm: vi.fn() },
}));

function renderPage(url: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[url]}>
        <UnsubscribePage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const notification = () => i18n.t("notifications.notify_reminder_due.label");

describe("UnsubscribePage", () => {
  beforeAll(async () => {
    await i18n.changeLanguage("es");
  });
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("only asks when opened, and unsubscribes after confirming", async () => {
    // Abrir la página no da de baja: los escáneres de correo abren los enlaces.
    vi.mocked(unsubscribeService.describe).mockResolvedValue({
      kind: "reminder_due",
    });
    vi.mocked(unsubscribeService.confirm).mockResolvedValue({
      kind: "reminder_due",
    });
    renderPage("/unsubscribe?token=abc");

    expect(
      await screen.findByText(
        i18n.t("unsubscribe.question", { notification: notification() }),
      ),
    ).toBeInTheDocument();
    expect(unsubscribeService.confirm).not.toHaveBeenCalled();

    await userEvent.click(
      screen.getByRole("button", { name: i18n.t("unsubscribe.confirm") }),
    );

    expect(unsubscribeService.confirm).toHaveBeenCalledWith("abc");
    expect(
      await screen.findByText(
        i18n.t("unsubscribe.done", { notification: notification() }),
      ),
    ).toBeInTheDocument();
  });

  it("explains an invalid link", async () => {
    vi.mocked(unsubscribeService.describe).mockRejectedValue(
      new ApiError(
        400,
        "Invalid unsubscribe link",
        "invalid_unsubscribe_token",
      ),
    );
    renderPage("/unsubscribe?token=forged");

    expect(
      await screen.findByText(i18n.t("errors.invalid_unsubscribe_token")),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("explains a link without token without calling the API", () => {
    renderPage("/unsubscribe");

    expect(
      screen.getByText(i18n.t("errors.invalid_unsubscribe_token")),
    ).toBeInTheDocument();
    expect(unsubscribeService.describe).not.toHaveBeenCalled();
  });
});
