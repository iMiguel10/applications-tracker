import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import i18n from "@/shared/i18n/i18n";
import { metaService } from "@/features/meta/services/meta.service";
import { LoginPage } from "./LoginPage";
import { RegisterPage } from "./RegisterPage";

// El selector de tema del AuthLayout, sin el ThemeProvider (matchMedia en jsdom).
vi.mock("@/app/providers/useTheme", () => ({
  useTheme: () => ({
    theme: "light",
    resolvedTheme: "light",
    setTheme: vi.fn(),
    setForceLight: vi.fn(),
  }),
}));
vi.mock("@/features/meta/services/meta.service", () => ({
  metaService: { get: vi.fn() },
}));

function renderPage(page: "login" | "register", signupEnabled: boolean) {
  vi.mocked(metaService.get).mockResolvedValue({
    email_enabled: true,
    signup_enabled: signupEnabled,
    max_document_bytes: 5 * 1024 * 1024,
  });
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{page === "login" ? <LoginPage /> : <RegisterPage />}</MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeAll(async () => {
  // AuthLayout ajusta el titular con ResizeObserver, que jsdom no tiene.
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
  await i18n.changeLanguage("es");
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Registro cerrado (decisión 0022)", () => {
  it("con el registro abierto, el login ofrece crear una cuenta y el registro tiene su formulario", async () => {
    renderPage("login", true);
    expect(await screen.findByRole("link", { name: i18n.t("auth.signUp") })).toHaveAttribute(
      "href",
      "/register",
    );
    cleanup();

    renderPage("register", true);
    expect(await screen.findByLabelText(i18n.t("auth.fields.email"))).toBeInTheDocument();
  });

  it("cerrado, el login no ofrece crear una cuenta", async () => {
    renderPage("login", false);

    await vi.waitFor(() => expect(metaService.get).toHaveBeenCalled());
    await vi.waitFor(() =>
      expect(screen.queryByRole("link", { name: i18n.t("auth.signUp") })).not.toBeInTheDocument(),
    );
    expect(screen.queryByText(i18n.t("auth.noAccount"))).not.toBeInTheDocument();
  });

  it("cerrado, el registro lo explica en lugar del formulario y lleva al login", async () => {
    renderPage("register", false);

    expect(
      await screen.findByRole("heading", { name: i18n.t("auth.signupClosed.title") }),
    ).toBeInTheDocument();
    expect(screen.getByText(i18n.t("auth.signupClosed.description"))).toBeInTheDocument();
    expect(screen.queryByLabelText(i18n.t("auth.fields.email"))).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: i18n.t("auth.signIn") })).toHaveAttribute(
      "href",
      "/login",
    );
  });
});
