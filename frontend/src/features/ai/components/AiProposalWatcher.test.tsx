import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { toast } from "sonner";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "@/shared/i18n/i18n";
import { ApiError } from "@/shared/lib/apiClient";
import {
  PROPOSAL_TOAST_MS,
  resetWatchedProposalsCache,
  watchProposal,
  type WatchedProposal,
} from "../lib/watchedProposals";
import { aiService } from "../services/ai.service";
import type { AiProposal } from "../types/Ai";
import { AiProposalWatcher } from "./AiProposalWatcher";

vi.mock("../services/ai.service", () => ({ aiService: { getProposal: vi.fn() } }));
vi.mock("@/features/auth/hooks/queries/useMe", () => ({
  useMe: () => ({ data: { id: "user-1", email: "ana@example.com" } }),
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const ENTRY: WatchedProposal = {
  proposalId: "p-1",
  applicationId: "app-1",
  userId: "user-1",
  kind: "cv",
  position: "Backend Developer",
  company: "Acme",
};

const proposal = (fields: Partial<AiProposal>): AiProposal => ({
  id: "p-1",
  application_id: "app-1",
  kind: "cv",
  status: "succeeded",
  language: "es",
  key_source: "platform",
  provider: "ollama",
  model: "qwen3:8b",
  error_code: null,
  proposal: null,
  created_at: "2026-10-17T10:00:00Z",
  updated_at: "2026-10-17T10:02:00Z",
  ...fields,
});

const watched = (): WatchedProposal[] =>
  JSON.parse(sessionStorage.getItem("ai.watchedProposals") ?? "[]") as WatchedProposal[];

function renderWatcher(path = "/dashboard") {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <AiProposalWatcher />
        <Routes>
          <Route path="*" element={<p>página</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeAll(async () => {
  await i18n.changeLanguage("es");
});

beforeEach(() => {
  sessionStorage.clear();
  resetWatchedProposalsCache();
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.useRealTimers();
});

describe("AiProposalWatcher", () => {
  it("sin propuestas vigiladas no pregunta nada", async () => {
    renderWatcher();

    await screen.findByText("página");
    expect(aiService.getProposal).not.toHaveBeenCalled();
  });

  it("avisa desde cualquier página cuando la propuesta está lista, con un enlace a revisarla", async () => {
    watchProposal(ENTRY);
    vi.mocked(aiService.getProposal).mockResolvedValue(proposal({}));

    renderWatcher("/calendar");

    await vi.waitFor(() => expect(toast.success).toHaveBeenCalledTimes(1));
    const [message, options] = vi.mocked(toast.success).mock.calls[0];
    expect(message).toBe("Tu CV adaptado para Backend Developer en Acme está listo.");
    expect(options).toMatchObject({ duration: PROPOSAL_TOAST_MS, action: { label: "Revisar" } });
    // Avisada: deja de vigilarla.
    expect(watched()).toEqual([]);
  });

  it("si falla, dice por qué y lleva a la solicitud (también estando en ella)", async () => {
    watchProposal({ ...ENTRY, kind: "cover_letter" });
    vi.mocked(aiService.getProposal).mockResolvedValue(
      proposal({ kind: "cover_letter", status: "failed", error_code: "ai_provider_unavailable" }),
    );

    renderWatcher("/applications/app-1");

    await vi.waitFor(() => expect(toast.error).toHaveBeenCalledTimes(1));
    const [message, options] = vi.mocked(toast.error).mock.calls[0];
    expect(message).toBe("No se pudo escribir tu carta para Backend Developer en Acme.");
    expect(options).toMatchObject({
      description: i18n.t("ai.errors.ai_provider_unavailable"),
      action: { label: "Ver la solicitud" },
    });
    expect(toast.success).not.toHaveBeenCalled();
  });

  it("en la página de revisión de esa propuesta no avisa: ya se ve allí", async () => {
    watchProposal(ENTRY);
    vi.mocked(aiService.getProposal).mockResolvedValue(proposal({}));

    renderWatcher("/applications/app-1/ai/p-1");

    await vi.waitFor(() => expect(watched()).toEqual([]));
    expect(toast.success).not.toHaveBeenCalled();
  });

  it("pregunta mientras está en curso, avisa una sola vez y deja de preguntar", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    watchProposal(ENTRY);
    vi.mocked(aiService.getProposal)
      .mockResolvedValueOnce(proposal({ status: "running" }))
      .mockResolvedValue(proposal({}));

    renderWatcher();

    await vi.waitFor(() => expect(aiService.getProposal).toHaveBeenCalledTimes(1));
    expect(toast.success).not.toHaveBeenCalled();
    await act(() => vi.advanceTimersByTimeAsync(2_100));
    await vi.waitFor(() => expect(toast.success).toHaveBeenCalledTimes(1));
    await act(() => vi.advanceTimersByTimeAsync(10_000));
    expect(aiService.getProposal).toHaveBeenCalledTimes(2);
    expect(toast.success).toHaveBeenCalledTimes(1);
  });

  it("no consulta las de otra cuenta (se cerró sesión en la pestaña) y las olvida", async () => {
    watchProposal({ ...ENTRY, userId: "user-2" });

    renderWatcher();

    await vi.waitFor(() => expect(watched()).toEqual([]));
    expect(aiService.getProposal).not.toHaveBeenCalled();
  });

  it("si la propuesta ya no existe, la olvida sin avisar", async () => {
    watchProposal(ENTRY);
    vi.mocked(aiService.getProposal).mockRejectedValue(new ApiError(404, "Not found", "not_found"));

    renderWatcher();

    await vi.waitFor(() => expect(watched()).toEqual([]));
    expect(toast.success).not.toHaveBeenCalled();
    expect(toast.error).not.toHaveBeenCalled();
  });
});
