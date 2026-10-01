import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import i18n from "@/shared/i18n/i18n";
import { applicationStatusChangeService } from "@/features/applications/services/applicationStatusChange.service";
import type { BoardFilters } from "../services/board.service";
import type { Board } from "../types/Board";
import { ApplicationBoard } from "./ApplicationBoard";

// jsdom no trae ResizeObserver y @dnd-kit/dom lo usa ya al importarse.
vi.hoisted(() => {
  globalThis.ResizeObserver ??= class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
});

vi.mock("@/features/applications/services/applicationStatusChange.service", () => ({
  applicationStatusChangeService: { create: vi.fn() },
}));

const FILTERS: BoardFilters = {
  status: [],
  company_id: null,
  work_mode: [],
  source: [],
  applied_from: null,
  applied_to: null,
  q: null,
};

const BOARD: Board = {
  columns: [
    {
      status: "applied",
      total: 3,
      items: [
        {
          id: "app-1",
          position_title: "Data engineer",
          company: { id: "c1", name: "Globex" },
          status_since: new Date().toISOString(),
        },
      ],
      allowed_transitions: ["screening", "rejected"],
    },
    {
      status: "rejected",
      total: 1,
      items: [
        {
          id: "app-2",
          position_title: "QA lead",
          company: { id: "c1", name: "Globex" },
          status_since: new Date().toISOString(),
        },
      ],
      allowed_transitions: [],
    },
  ],
};

function renderBoard() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ApplicationBoard
          board={BOARD}
          filters={FILTERS}
          listHref={(status) => `/applications?status=${status}`}
        />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const column = (status: string) =>
  screen.getByRole("listitem", { name: new RegExp(`^${i18n.t(`applications.status.${status}`)}:`) });

describe("ApplicationBoard", () => {
  beforeAll(async () => {
    await i18n.changeLanguage("es");
  });
  afterEach(() => {
    cleanup();
    localStorage.clear();
    vi.clearAllMocks();
  });

  it("shows each card with its company, days and the link to the rest of the column", () => {
    renderBoard();

    const applied = column("applied");
    expect(within(applied).getByRole("link", { name: "Data engineer" })).toHaveAttribute(
      "href",
      "/applications/app-1",
    );
    expect(within(applied).getByText("Globex")).toBeInTheDocument();
    expect(within(applied).getByText(i18n.t("board.sinceToday"))).toBeInTheDocument();
    // 3 en total y 1 tarjeta: "y 2 más" lleva al listado de ese estado.
    expect(within(applied).getByRole("link", { name: i18n.t("board.more", { count: 2 }) })).toHaveAttribute(
      "href",
      "/applications?status=applied",
    );
  });

  it("gives a card in a final status neither drag handle nor move menu", () => {
    renderBoard();
    const label = "QA lead · Globex";

    expect(screen.queryByRole("button", { name: i18n.t("board.dnd.handle", { label }) })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: i18n.t("board.moveTo", { label }) })).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: i18n.t("board.dnd.handle", { label: "Data engineer · Globex" }) }),
    ).toBeInTheDocument();
  });

  it("moves without dragging: the menu offers only the allowed statuses and opens the dialog with one chosen", async () => {
    const user = userEvent.setup();
    renderBoard();

    await user.click(
      screen.getByRole("button", { name: i18n.t("board.moveTo", { label: "Data engineer · Globex" }) }),
    );
    const items = await screen.findAllByRole("menuitem");
    expect(items.map((item) => item.textContent)).toEqual([
      i18n.t("applications.status.screening"),
      i18n.t("applications.status.rejected"),
    ]);

    await user.click(items[1]);
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText(i18n.t("applications.changeStatusTitle"))).toBeInTheDocument();
    // El destino del menú ya está elegido; solo falta confirmar (o añadir nota y fecha).
    expect(within(dialog).getByRole("combobox")).toHaveTextContent(i18n.t("applications.status.rejected"));
    expect(applicationStatusChangeService.create).not.toHaveBeenCalled();
  });

  it("folds only the final-status columns and keeps the count visible", async () => {
    const user = userEvent.setup();
    renderBoard();

    expect(
      within(column("applied")).queryByRole("button", {
        name: i18n.t("board.collapse", { column: i18n.t("applications.status.applied") }),
      }),
    ).not.toBeInTheDocument();

    const rejected = i18n.t("applications.status.rejected");
    const fold = screen.getByRole("button", { name: i18n.t("board.collapse", { column: rejected }) });
    expect(fold).toHaveAttribute("aria-expanded", "true");
    await user.click(fold);

    const unfold = screen.getByRole("button", { name: i18n.t("board.expand", { column: rejected }) });
    expect(unfold).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("link", { name: "QA lead" })).not.toBeInTheDocument();
    expect(within(column("rejected")).getByText("1")).toBeInTheDocument();

    await user.click(unfold);
    expect(screen.getByRole("link", { name: "QA lead" })).toBeInTheDocument();
  });
});
