import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import i18n from "@/shared/i18n/i18n";
import { ApiError } from "@/shared/lib/apiClient";
import { metaService } from "@/features/meta/services/meta.service";
import { authService } from "../services/auth.service";
import { ChangePasswordCard } from "./ChangePasswordCard";
import { makeMeta } from "@/test/meta";

vi.mock("@/features/meta/services/meta.service", () => ({
  metaService: { get: vi.fn() },
}));
vi.mock("../services/auth.service", () => ({
  authService: { changePassword: vi.fn(), sendPasswordResetEmail: vi.fn() },
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const EMAIL = "ana@example.com";

function renderCard({ emailEnabled }: { emailEnabled: boolean }) {
  vi.mocked(metaService.get).mockResolvedValue(
    makeMeta({ email_enabled: emailEnabled, signup_enabled: true }),
  );
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <ChangePasswordCard email={EMAIL} />
    </QueryClientProvider>,
  );
}

async function fill(current: string, next: string, confirm = next) {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText(i18n.t("account.password.current")), current);
  await user.type(screen.getByLabelText(i18n.t("account.password.new")), next);
  await user.type(screen.getByLabelText(i18n.t("account.password.confirm")), confirm);
  await user.click(screen.getByRole("button", { name: i18n.t("account.password.submit") }));
}

beforeAll(async () => {
  await i18n.changeLanguage("es");
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ChangePasswordCard (issue #2)", () => {
  it("cambia la contraseña con la actual y vacía el formulario", async () => {
    vi.mocked(authService.changePassword).mockResolvedValue(undefined);
    renderCard({ emailEnabled: false });

    await fill("actual-1", "nueva-clave-2");

    await waitFor(() =>
      expect(authService.changePassword).toHaveBeenCalledWith("actual-1", "nueva-clave-2"),
    );
    await waitFor(() =>
      expect(screen.getByLabelText(i18n.t("account.password.current"))).toHaveValue(""),
    );
  });

  it("no envía nada si la nueva no coincide al repetirla", async () => {
    renderCard({ emailEnabled: false });

    await fill("actual-1", "nueva-clave-2", "otra-cosa-3");

    expect(
      await screen.findByText(i18n.t("auth.validation.passwordsDoNotMatch")),
    ).toBeInTheDocument();
    expect(authService.changePassword).not.toHaveBeenCalled();
  });

  it("marca el campo de la actual si no es correcta", async () => {
    vi.mocked(authService.changePassword).mockRejectedValue(
      new ApiError(400, "The current password is wrong", "wrong_current_password"),
    );
    renderCard({ emailEnabled: false });

    await fill("no-es-1", "nueva-clave-2");

    const current = screen.getByLabelText(i18n.t("account.password.current"));
    await waitFor(() => expect(current).toHaveAttribute("aria-invalid", "true"));
    expect(screen.getByText(i18n.t("account.password.wrongCurrent"))).toBeInTheDocument();
  });

  it("explica la política en el campo de la nueva", async () => {
    vi.mocked(authService.changePassword).mockRejectedValue(
      new ApiError(422, "policy", "password_policy"),
    );
    renderCard({ emailEnabled: false });

    await fill("actual-1", "corta");

    expect(await screen.findByText(i18n.t("auth.errors.passwordPolicy"))).toBeInTheDocument();
    expect(screen.getByLabelText(i18n.t("account.password.new"))).toHaveAttribute(
      "aria-invalid",
      "true",
    );
  });

  it("con correo, ofrece el enlace para quien ha olvidado la actual", async () => {
    vi.mocked(authService.sendPasswordResetEmail).mockResolvedValue("ok");
    renderCard({ emailEnabled: true });
    const user = userEvent.setup();

    await user.click(
      await screen.findByRole("button", { name: i18n.t("account.password.send") }),
    );

    expect(vi.mocked(authService.sendPasswordResetEmail).mock.calls[0][0]).toBe(EMAIL);
    expect(
      await screen.findByText(i18n.t("account.password.sent", { email: EMAIL })),
    ).toBeInTheDocument();
  });

  it("sin correo, solo el formulario: no hay enlace que enviar", async () => {
    renderCard({ emailEnabled: false });

    await waitFor(() => expect(metaService.get).toHaveBeenCalled());
    expect(screen.getByLabelText(i18n.t("account.password.current"))).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: i18n.t("account.password.send") }),
    ).not.toBeInTheDocument();
  });
});
