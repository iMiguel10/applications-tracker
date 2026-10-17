import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import i18n from "@/shared/i18n/i18n";
import { usageService } from "@/features/usage/services/usage.service";
import type { ApplicationDetail } from "@/features/applications/types/Application";
import { aiService } from "../services/ai.service";
import type { AiConsents, AiKeys, AiProposal } from "../types/Ai";
import { AiTailorCard } from "./AiTailorCard";

vi.mock("../services/ai.service", () => ({
  aiService: {
    consents: vi.fn(),
    keys: vi.fn(),
    grantConsent: vi.fn(),
    listProposals: vi.fn(),
    requestProposal: vi.fn(),
  },
}));
vi.mock("@/features/usage/services/usage.service", () => ({ usageService: { get: vi.fn() } }));
vi.mock("@/features/auth/hooks/useAccountZone", () => ({ useAccountZone: () => "Europe/Madrid" }));

const OFFER = "Backend con Python, FastAPI y PostgreSQL. ".repeat(8);

const consents = (granted: boolean, provider: AiConsents["platform_provider"] = "groq") => ({
  text_version: 1,
  platform_provider: provider,
  platform_model: "openai/gpt-oss-120b",
  consents: granted
    ? [{ provider: "groq" as const, granted: true, granted_at: "2026-10-07T10:00:00Z", revoked_at: null }]
    : [],
});

const NO_KEYS: AiKeys = { own_keys_enabled: false, providers: [], active_provider: null };

const ANTHROPIC_ACTIVE: AiKeys = {
  own_keys_enabled: true,
  providers: [
    {
      provider: "anthropic",
      models: ["claude-sonnet-5-5"],
      key: {
        model: "claude-sonnet-5-5",
        last4: "abcd",
        validated_at: "2026-10-08T10:00:00Z",
        model_allowed: true,
      },
    },
  ],
  active_provider: "anthropic",
};

const proposal = (fields: Partial<AiProposal>): AiProposal => ({
  id: "p-1",
  application_id: "app-1",
  kind: "cv",
  status: "succeeded",
  language: "es",
  key_source: "platform",
  provider: "groq",
  model: "openai/gpt-oss-120b",
  error_code: null,
  proposal: null,
  created_at: "2026-10-07T10:00:00Z",
  updated_at: "2026-10-07T10:00:05Z",
  ...fields,
});

function renderCard({
  description = OFFER,
  granted = true,
  provider = "groq" as AiConsents["platform_provider"],
  remaining = 1,
  letterRemaining = 1,
  proposals = [] as AiProposal[],
  keys = NO_KEYS,
} = {}) {
  vi.mocked(aiService.consents).mockResolvedValue(consents(granted, provider));
  vi.mocked(aiService.keys).mockResolvedValue(keys);
  vi.mocked(aiService.listProposals).mockResolvedValue(proposals);
  vi.mocked(usageService.get).mockResolvedValue({
    warning_ratio: 0.8,
    limits: [
      { key: "ai_cv_proposals", used: 1 - remaining, limit: 1, remaining, renews: false, unit: "count" },
      {
        key: "ai_cover_letter_proposals",
        used: 1 - letterRemaining,
        limit: 1,
        remaining: letterRemaining,
        renews: false,
        unit: "count",
      },
    ],
  });
  const application = { id: "app-1", job_description: description } as ApplicationDetail;
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AiTailorCard application={application} />
      </MemoryRouter>
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

describe("AiTailorCard", () => {
  it("no se ofrece si la instalación no tiene IA", async () => {
    renderCard({ provider: null });

    await vi.waitFor(() => expect(aiService.consents).toHaveBeenCalled());
    expect(screen.queryByText(i18n.t("ai.tailor.title"))).not.toBeInTheDocument();
  });

  it("explica que falta la oferta, o que es demasiado corta, sin dejar pedirla", async () => {
    renderCard({ description: "" });
    expect(await screen.findByText(/añade antes la descripción de la oferta/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: i18n.t("ai.tailor.request.cv") })).not.toBeInTheDocument();
    cleanup();

    renderCard({ description: "Backend" });
    expect(await screen.findByText(/necesita al menos 200 caracteres/)).toBeInTheDocument();
  });

  describe("sin usos gratuitos, dice cómo seguir (RF-156)", () => {
    const OFFERED: AiKeys = {
      own_keys_enabled: true,
      providers: [
        { provider: "anthropic", models: ["claude-sonnet-5-5"], key: null },
        { provider: "openai", models: ["gpt-5.5"], key: null },
        { provider: "groq", models: ["openai/gpt-oss-120b"], key: null },
      ],
      active_provider: null,
    };
    const settingsLink = (name: string) => {
      const link = screen.getByRole("link", { name });
      expect(link).toHaveAttribute("href", "/preferences#ai-settings");
    };

    it("sin clave: los proveedores que ofrece la instalación y que se paga aparte", async () => {
      renderCard({ remaining: 0, keys: OFFERED });

      const text = await screen.findByText(/Para seguir, añade tu clave de/);
      expect(text).toHaveTextContent("Anthropic, OpenAI o Groq");
      expect(text).toHaveTextContent("unos céntimos");
      settingsLink(i18n.t("ai.tailor.addKey"));
    });

    it("con una clave guardada pero sin usar: elegirla", async () => {
      const withGroq: AiKeys = {
        ...OFFERED,
        providers: OFFERED.providers.map((option) =>
          option.provider === "groq"
            ? {
                ...option,
                key: {
                  model: "openai/gpt-oss-120b",
                  last4: "abcd",
                  validated_at: "2026-10-08T10:00:00Z",
                  model_allowed: true,
                },
              }
            : option,
        ),
      };
      renderCard({ remaining: 0, keys: withGroq });

      const text = await screen.findByText(/que ya tienes guardada/);
      expect(text).toHaveTextContent("tu clave de Groq");
      settingsLink(i18n.t("ai.tailor.useSavedKey"));
    });

    it("sin claves propias en la instalación: lo dice, sin enlace", async () => {
      renderCard({ remaining: 0 });

      expect(await screen.findByText(/no admite claves propias/)).toBeInTheDocument();
      expect(screen.queryByRole("link")).not.toBeInTheDocument();
    });
  });

  it("sin usos gratuitos de CV lo dice, y la carta sigue disponible con los suyos", async () => {
    renderCard({ remaining: 0 });

    expect(await screen.findByText(new RegExp(i18n.t("ai.tailor.noUses.cv")))).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: i18n.t("ai.tailor.request.cv") })).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: i18n.t("ai.tailor.request.cover_letter") }),
    ).toBeInTheDocument();
  });

  it("la carta pide el consentimiento la primera vez y después la propuesta de carta", async () => {
    const user = userEvent.setup();
    vi.mocked(aiService.grantConsent).mockResolvedValue(consents(true));
    vi.mocked(aiService.requestProposal).mockResolvedValue(
      proposal({ kind: "cover_letter", status: "queued" }),
    );
    renderCard({ granted: false });

    await user.click(
      await screen.findByRole("button", { name: i18n.t("ai.tailor.request.cover_letter") }),
    );
    await user.click(await screen.findByRole("button", { name: i18n.t("ai.consent.accept") }));

    await vi.waitFor(() =>
      expect(aiService.requestProposal).toHaveBeenCalledWith("app-1", "cover_letter", "es"),
    );
  });

  it("dice de qué tipo es cada propuesta", async () => {
    renderCard({ proposals: [proposal({ id: "p-letter", kind: "cover_letter" })] });

    expect(await screen.findByText(/^Carta · /)).toBeInTheDocument();
  });

  it("la primera vez pide el consentimiento y después la propuesta", async () => {
    const user = userEvent.setup();
    vi.mocked(aiService.grantConsent).mockResolvedValue(consents(true));
    vi.mocked(aiService.requestProposal).mockResolvedValue(proposal({ status: "queued" }));
    renderCard({ granted: false });

    await user.click(await screen.findByRole("button", { name: i18n.t("ai.tailor.request.cv") }));
    expect(aiService.requestProposal).not.toHaveBeenCalled();
    const dialog = await screen.findByRole("dialog");
    expect(dialog).toHaveTextContent("Groq");
    await user.click(screen.getByRole("button", { name: i18n.t("ai.consent.accept") }));

    await vi.waitFor(() =>
      expect(aiService.requestProposal).toHaveBeenCalledWith("app-1", "cv", "es"),
    );
    expect(vi.mocked(aiService.grantConsent).mock.calls[0][0]).toBe("groq");
  });

  it("con consentimiento pide la propuesta en el idioma elegido", async () => {
    const user = userEvent.setup();
    vi.mocked(aiService.requestProposal).mockResolvedValue(proposal({ status: "queued" }));
    renderCard();

    await user.click(await screen.findByRole("button", { name: i18n.t("ai.tailor.languages.en") }));
    await user.click(screen.getByRole("button", { name: i18n.t("ai.tailor.request.cv") }));

    await vi.waitFor(() =>
      expect(aiService.requestProposal).toHaveBeenCalledWith("app-1", "cv", "en"),
    );
    expect(aiService.grantConsent).not.toHaveBeenCalled();
  });

  it("enlaza a revisar la terminada y explica la que falló", async () => {
    renderCard({
      proposals: [
        proposal({ id: "p-ok" }),
        proposal({ id: "p-bad", status: "invalid", error_code: "ai_response_invalid" }),
      ],
    });

    const review = await screen.findByRole("link", { name: i18n.t("ai.tailor.review") });
    expect(review).toHaveAttribute("href", "/applications/app-1/ai/p-ok");
    expect(screen.getByText(i18n.t("ai.errors.ai_response_invalid"))).toBeInTheDocument();
  });

  it("con clave propia activa la usa y no mira los usos gratuitos", async () => {
    const user = userEvent.setup();
    vi.mocked(aiService.grantConsent).mockResolvedValue(consents(true));
    vi.mocked(aiService.requestProposal).mockResolvedValue(proposal({ status: "queued" }));
    renderCard({ keys: ANTHROPIC_ACTIVE, remaining: 0, granted: false });

    expect(await screen.findByText(/Con tu clave de Anthropic/)).toBeInTheDocument();
    expect(screen.queryByText(new RegExp(i18n.t("ai.tailor.noUses.cv")))).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: i18n.t("ai.tailor.request.cv") }));
    // El consentimiento se pide para el proveedor de la clave, no el de la plataforma.
    expect(await screen.findByRole("dialog")).toHaveTextContent("Anthropic");
    await user.click(screen.getByRole("button", { name: i18n.t("ai.consent.accept") }));
    await vi.waitFor(() => expect(aiService.grantConsent).toHaveBeenCalled());
    expect(vi.mocked(aiService.grantConsent).mock.calls[0][0]).toBe("anthropic");
  });

  it("sin usos gratuitos en la instalación, lleva a añadir una clave", async () => {
    renderCard({ provider: null, keys: { ...NO_KEYS, own_keys_enabled: true } });

    expect(await screen.findByRole("link", { name: i18n.t("ai.tailor.addKey") })).toHaveAttribute(
      "href",
      "/preferences#ai-settings",
    );
    expect(screen.queryByRole("button", { name: i18n.t("ai.tailor.request.cv") })).not.toBeInTheDocument();
  });
});
