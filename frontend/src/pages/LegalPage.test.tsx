import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "@/shared/i18n/i18n";
import { metaService } from "@/features/meta/services/meta.service";
import type { LegalInfo } from "@/features/meta/types/Meta";
import { LegalLinks } from "@/features/legal/components/LegalLinks";
import { makeMeta, NO_LEGAL, SOME_LEGAL } from "@/test/meta";
import { LegalPage } from "./LegalPage";

vi.mock("@/features/meta/services/meta.service", () => ({
  metaService: { get: vi.fn() },
}));

function renderPage(
  path: string,
  { legal = SOME_LEGAL, emailEnabled = true }: { legal?: LegalInfo; emailEnabled?: boolean } = {},
) {
  vi.mocked(metaService.get).mockResolvedValue(
    makeMeta({ legal, email_enabled: emailEnabled }),
  );
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/legal/:page" element={<LegalPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(async () => {
  await i18n.changeLanguage("es");
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("LegalPage (issue #3)", () => {
  it("sin responsable configurado, lo dice en vez de inventar datos", async () => {
    renderPage("/legal/privacy", { legal: NO_LEGAL });

    expect(await screen.findByText(i18n.t("legal.notConfigured.title"))).toBeInTheDocument();
    expect(screen.queryByText(/Quién trata tus datos/)).not.toBeInTheDocument();
  });

  it("la privacidad nombra al responsable, su contacto y cuánto siguen los datos en las copias", async () => {
    renderPage("/legal/privacy", {
      legal: { ...SOME_LEGAL, tax_id: "12345678Z", backup_retention_days: 35 },
    });

    expect(await screen.findByText(/Ana García/)).toBeInTheDocument();
    expect(screen.getByText(/NIF 12345678Z/)).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "privacidad@example.com" }).length).toBeGreaterThan(0);
    expect(screen.getByText("35 días")).toBeInTheDocument();
    expect(screen.getByText(i18n.t("legal.version", { version: SOME_LEGAL.version }))).toBeInTheDocument();
    expect(screen.getByText(/Agencia Española de Protección de Datos/)).toBeInTheDocument();
  });

  it("con IA de la plataforma en EE. UU., dice a quién van los datos y la transferencia", async () => {
    renderPage("/legal/privacy", { legal: { ...SOME_LEGAL, ai_platform_provider: "groq" } });

    expect(await screen.findByText(/Está en Estados Unidos/)).toBeInTheDocument();
    expect(screen.getByText(/sin tus datos de contacto/)).toBeInTheDocument();
  });

  it("sin IA ni correo, no los nombra", async () => {
    renderPage("/legal/privacy", { emailEnabled: false });

    await screen.findByText(/Quién trata tus datos/);
    expect(screen.queryByText(/inteligencia artificial:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/servicio de correo/)).not.toBeInTheDocument();
  });

  it("con Ollama, no habla de transferencias a EE. UU.", async () => {
    renderPage("/legal/privacy", { legal: { ...SOME_LEGAL, ai_platform_provider: "ollama" } });

    expect(await screen.findByText(/Ollama/)).toBeInTheDocument();
    expect(screen.queryByText(/Estados Unidos/)).not.toBeInTheDocument();
  });

  it("una autoridad de control propia sustituye a la AEPD", async () => {
    renderPage("/legal/privacy", { legal: { ...SOME_LEGAL, supervisory_authority: "la CNIL" } });

    expect(await screen.findByText(/reclamar ante la CNIL/)).toBeInTheDocument();
  });

  it("en inglés, los textos en inglés", async () => {
    await i18n.changeLanguage("en");
    renderPage("/legal/terms");

    expect(await screen.findByRole("heading", { name: "The service" })).toBeInTheDocument();
  });

  it("enlaza a las demás páginas legales", async () => {
    renderPage("/legal/cookies");

    expect(await screen.findByRole("link", { name: i18n.t("legal.nav.privacy") })).toHaveAttribute(
      "href",
      "/legal/privacy",
    );
  });
});

describe("LegalLinks (issue #3)", () => {
  function renderLinks(legal: LegalInfo) {
    vi.mocked(metaService.get).mockResolvedValue(makeMeta({ legal }));
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <LegalLinks />
        </MemoryRouter>
      </QueryClientProvider>,
    );
  }

  it("con la instalación configurada, enlaza las cuatro páginas", async () => {
    renderLinks(SOME_LEGAL);

    expect(await screen.findByRole("link", { name: i18n.t("legal.nav.notice") })).toBeInTheDocument();
    expect(screen.getAllByRole("link")).toHaveLength(4);
  });

  it("en una instalación de uso personal no aparece", async () => {
    renderLinks(NO_LEGAL);

    await vi.waitFor(() => expect(metaService.get).toHaveBeenCalled());
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});
