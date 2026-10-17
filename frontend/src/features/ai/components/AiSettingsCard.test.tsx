import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import i18n from "@/shared/i18n/i18n";
import { aiService } from "../services/ai.service";
import type { AiConsents, AiKeys } from "../types/Ai";
import { AiSettingsCard } from "./AiSettingsCard";

vi.mock("../services/ai.service", () => ({
  aiService: {
    consents: vi.fn(),
    keys: vi.fn(),
    saveKey: vi.fn(),
    changeKeyModel: vi.fn(),
    deleteKey: vi.fn(),
    setActiveProvider: vi.fn(),
    revokeConsent: vi.fn(),
  },
}));
vi.mock("@/features/auth/hooks/useAccountZone", () => ({ useAccountZone: () => "Europe/Madrid" }));

const USER_KEY = "sk-ant-api-1234567890SECRET";

const CONSENTS: AiConsents = {
  text_version: 1,
  platform_provider: "groq",
  platform_model: "openai/gpt-oss-120b",
  consents: [
    { provider: "groq", granted: true, granted_at: "2026-10-07T10:00:00Z", revoked_at: null },
  ],
};

const KEYS: AiKeys = {
  own_keys_enabled: true,
  providers: [
    { provider: "anthropic", models: ["claude-sonnet-5-5", "claude-haiku-5-5"], key: null },
    {
      provider: "openai",
      models: ["gpt-5.5", "gpt-5.4-mini"],
      key: {
        model: "gpt-5.5",
        last4: "wxyz",
        validated_at: "2026-10-08T10:00:00Z",
        model_allowed: true,
      },
    },
  ],
  active_provider: "openai",
};

function renderCard(keys: AiKeys = KEYS, consents: AiConsents = CONSENTS) {
  vi.mocked(aiService.keys).mockResolvedValue(keys);
  vi.mocked(aiService.consents).mockResolvedValue(consents);
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <AiSettingsCard />
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

describe("AiSettingsCard", () => {
  it("no aparece si la instalación no tiene IA", async () => {
    renderCard({ ...KEYS, own_keys_enabled: false }, { ...CONSENTS, platform_provider: null });

    await vi.waitFor(() => expect(aiService.keys).toHaveBeenCalled());
    expect(screen.queryByText(i18n.t("ai.settings.title"))).not.toBeInTheDocument();
  });

  it("dice dónde conseguir la clave de cada proveedor que aún no tiene una", async () => {
    renderCard();

    const link = await screen.findByRole("link", {
      name: i18n.t("ai.settings.getKeyLabel", { provider: "Anthropic" }),
    });
    expect(link).toHaveAttribute("href", "https://platform.claude.com/settings/keys");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    // OpenAI ya tiene clave: no hace falta decirle dónde conseguirla.
    expect(
      screen.queryByRole("link", { name: i18n.t("ai.settings.getKeyLabel", { provider: "OpenAI" }) }),
    ).not.toBeInTheDocument();
  });

  it("enseña las claves guardadas solo por sus 4 últimos caracteres", async () => {
    renderCard();

    expect(await screen.findByText(/Clave …wxyz/)).toBeInTheDocument();
    expect(screen.getByText(i18n.t("ai.settings.noKey"))).toBeInTheDocument();
  });

  it("guarda una clave con el modelo recomendado y la borra del formulario", async () => {
    const user = userEvent.setup();
    vi.mocked(aiService.saveKey).mockResolvedValue(KEYS);
    renderCard();

    const anthropic = (await screen.findByText("Anthropic")).closest("li")!;
    await user.click(within(anthropic).getByRole("button", { name: i18n.t("ai.settings.add") }));
    const input = within(anthropic).getByLabelText(/Clave de API de Anthropic/);
    expect(input).toHaveAttribute("type", "password");
    await user.type(input, USER_KEY);
    await user.click(within(anthropic).getByRole("button", { name: i18n.t("ai.settings.save") }));

    await vi.waitFor(() =>
      expect(aiService.saveKey).toHaveBeenCalledWith("anthropic", USER_KEY, "claude-sonnet-5-5"),
    );
    // Guardada, el formulario se cierra y la clave no queda en pantalla.
    await vi.waitFor(() => expect(screen.queryByDisplayValue(USER_KEY)).not.toBeInTheDocument());
  });

  it("borra una clave y retira un permiso de envío", async () => {
    const user = userEvent.setup();
    vi.mocked(aiService.deleteKey).mockResolvedValue(undefined);
    vi.mocked(aiService.revokeConsent).mockResolvedValue(undefined);
    renderCard();

    await user.click(await screen.findByRole("button", { name: "Borrar la clave de OpenAI" }));
    await user.click(screen.getByRole("button", { name: "Retirar el permiso a Groq" }));

    await vi.waitFor(() => expect(aiService.deleteKey).toHaveBeenCalledWith("openai"));
    await vi.waitFor(() => expect(aiService.revokeConsent).toHaveBeenCalledWith("groq"));
  });
});
