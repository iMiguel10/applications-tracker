import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import i18n from "@/shared/i18n/i18n";
import { ApiError } from "@/shared/lib/apiClient";
import { authService } from "@/features/auth/services/auth.service";
import { metaService } from "@/features/meta/services/meta.service";
import type { LegalInfo } from "@/features/meta/types/Meta";
import { makeMeta, NO_LEGAL, SOME_LEGAL } from "@/test/meta";
import { LegalGate } from "./LegalGate";

vi.mock("@/features/meta/services/meta.service", () => ({
  metaService: { get: vi.fn() },
}));
vi.mock("@/features/auth/services/auth.service", () => ({
  authService: { getMe: vi.fn(), acceptLegal: vi.fn(), signOut: vi.fn() },
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const APP = "Contenido de la aplicación";

function renderGate(legal: LegalInfo, accepted: string | null) {
  vi.mocked(metaService.get).mockResolvedValue(makeMeta({ legal }));
  vi.mocked(authService.getMe).mockResolvedValue({
    id: "u1",
    email: "ana@example.com",
    legal_accepted_version: accepted,
  });
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <LegalGate>
          <p>{APP}</p>
        </LegalGate>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const acceptButton = () => screen.findByRole("button", { name: i18n.t("legal.accept.button") });

beforeAll(async () => {
  await i18n.changeLanguage("es");
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("LegalGate (issue #3)", () => {
  it("sin aceptar la versión vigente, pide aceptarla en lugar de la aplicación", async () => {
    renderGate(SOME_LEGAL, null);

    expect(await acceptButton()).toBeInTheDocument();
    expect(screen.queryByText(APP)).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /términos y condiciones/ })).toHaveAttribute(
      "href",
      "/legal/terms",
    );
  });

  it("también si aceptó una versión anterior", async () => {
    renderGate(SOME_LEGAL, "2020-01-01");

    expect(await acceptButton()).toBeInTheDocument();
  });

  it("no acepta sin marcar la casilla", async () => {
    renderGate(SOME_LEGAL, null);
    const user = userEvent.setup();

    await user.click(await acceptButton());

    expect(screen.getByText(i18n.t("legal.consent.required"))).toBeInTheDocument();
    expect(authService.acceptLegal).not.toHaveBeenCalled();
  });

  it("al aceptar, guarda la versión vigente y deja pasar", async () => {
    vi.mocked(authService.acceptLegal).mockResolvedValue(undefined);
    renderGate(SOME_LEGAL, null);
    const user = userEvent.setup();

    await user.click(await screen.findByRole("checkbox"));
    await user.click(await acceptButton());

    await waitFor(() => expect(screen.getByText(APP)).toBeInTheDocument());
    expect(vi.mocked(authService.acceptLegal).mock.calls[0][0]).toBe(SOME_LEGAL.version);
  });

  it("si la versión cambió con la pantalla abierta, vuelve a pedir la nueva", async () => {
    vi.mocked(authService.acceptLegal).mockRejectedValue(
      new ApiError(409, "outdated", "legal_version_outdated"),
    );
    renderGate(SOME_LEGAL, null);
    const user = userEvent.setup();

    await user.click(await screen.findByRole("checkbox"));
    await user.click(await acceptButton());

    await waitFor(() => expect(metaService.get).toHaveBeenCalledTimes(2));
    expect(screen.queryByText(APP)).not.toBeInTheDocument();
  });

  it("con la versión vigente aceptada, la aplicación", async () => {
    renderGate(SOME_LEGAL, SOME_LEGAL.version);

    expect(await screen.findByText(APP)).toBeInTheDocument();
  });

  it("en una instalación sin textos legales, nunca la pide", async () => {
    renderGate(NO_LEGAL, null);

    expect(await screen.findByText(APP)).toBeInTheDocument();
    await waitFor(() => expect(authService.getMe).toHaveBeenCalled());
    expect(screen.queryByRole("button", { name: i18n.t("legal.accept.button") })).toBeNull();
  });
});
