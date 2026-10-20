import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import i18n from "@/shared/i18n/i18n";
import { metaService } from "@/features/meta/services/meta.service";
import type { LegalInfo } from "@/features/meta/types/Meta";
import { makeMeta, NO_LEGAL, SOME_LEGAL } from "@/test/meta";
import { authService } from "../services/auth.service";
import { RegisterForm } from "./RegisterForm";

vi.mock("@/features/meta/services/meta.service", () => ({
  metaService: { get: vi.fn() },
}));
vi.mock("../services/auth.service", () => ({
  authService: { signUp: vi.fn(), acceptLegal: vi.fn() },
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

function renderForm(legal: LegalInfo) {
  vi.mocked(metaService.get).mockResolvedValue(makeMeta({ legal }));
  vi.mocked(authService.signUp).mockResolvedValue({ status: "ok" });
  vi.mocked(authService.acceptLegal).mockResolvedValue(undefined);
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <RegisterForm />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

async function fill() {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText(i18n.t("auth.fields.email")), "ana@example.com");
  await user.type(screen.getByLabelText(i18n.t("auth.fields.password")), "clave-segura-1");
  await user.type(screen.getByLabelText(i18n.t("auth.fields.confirmPassword")), "clave-segura-1");
  return user;
}

beforeAll(async () => {
  await i18n.changeLanguage("es");
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("RegisterForm con textos legales (issue #3)", () => {
  it("no crea la cuenta sin aceptar los términos y la privacidad", async () => {
    renderForm(SOME_LEGAL);
    const user = await fill();

    await screen.findByRole("checkbox");
    await user.click(screen.getByRole("button", { name: i18n.t("auth.signUp") }));

    expect(await screen.findByText(i18n.t("legal.consent.required"))).toBeInTheDocument();
    expect(authService.signUp).not.toHaveBeenCalled();
  });

  it("al aceptarlos, crea la cuenta y deja apuntada la versión aceptada", async () => {
    renderForm(SOME_LEGAL);
    const user = await fill();

    await user.click(await screen.findByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: i18n.t("auth.signUp") }));

    await waitFor(() => expect(authService.acceptLegal).toHaveBeenCalled());
    expect(vi.mocked(authService.acceptLegal).mock.calls[0][0]).toBe(SOME_LEGAL.version);
  });

  it("sin textos legales, ni casilla ni aceptación", async () => {
    renderForm(NO_LEGAL);
    const user = await fill();

    await waitFor(() => expect(metaService.get).toHaveBeenCalled());
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: i18n.t("auth.signUp") }));

    await waitFor(() => expect(authService.signUp).toHaveBeenCalled());
    expect(authService.acceptLegal).not.toHaveBeenCalled();
  });
});
