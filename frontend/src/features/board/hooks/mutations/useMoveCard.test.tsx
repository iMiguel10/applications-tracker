import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { applicationStatusChangeService } from "@/features/applications/services/applicationStatusChange.service";
import { ApiError } from "@/shared/lib/apiClient";
import { boardKeys } from "../../board.keys";
import type { BoardFilters } from "../../services/board.service";
import type { Board } from "../../types/Board";
import { useMoveCard } from "./useMoveCard";

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

const SINCE = "2026-09-01T10:00:00.000Z";

const BOARD: Board = {
  columns: [
    {
      status: "applied",
      total: 2,
      items: [
        {
          id: "app-1",
          position_title: "Data engineer",
          company: { id: "c1", name: "Globex" },
          status_since: SINCE,
        },
        {
          id: "app-3",
          position_title: "SRE",
          company: { id: "c1", name: "Globex" },
          status_since: SINCE,
        },
      ],
      allowed_transitions: ["screening", "rejected"],
    },
    {
      status: "screening",
      total: 0,
      items: [],
      allowed_transitions: ["interviewing", "rejected"],
    },
  ],
};

function setup() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const key = boardKeys.board(FILTERS);
  queryClient.setQueryData(key, structuredClone(BOARD));
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  const hook = renderHook(() => useMoveCard(FILTERS), { wrapper });
  const board = () => queryClient.getQueryData<Board>(key);
  const column = (status: string) =>
    board()?.columns.find((item) => item.status === status);
  return { queryClient, key, hook, board, column };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe("useMoveCard", () => {
  afterEach(() => vi.clearAllMocks());

  it("moves the card to the target column before the API answers", async () => {
    const pending = deferred<never>();
    vi.mocked(applicationStatusChangeService.create).mockReturnValue(
      pending.promise,
    );
    const { hook, column } = setup();

    act(() => {
      hook.result.current.mutate({
        cardId: "app-1",
        from: "applied",
        to: "screening",
      });
    });

    await waitFor(() => expect(column("screening")?.total).toBe(1));
    expect(column("screening")?.items.map((card) => card.id)).toEqual(["app-1"]);
    expect(column("applied")?.items.map((card) => card.id)).toEqual(["app-3"]);
    expect(column("applied")?.total).toBe(1);
    pending.reject(new ApiError(500, "boom"));
    await waitFor(() => expect(hook.result.current.isError).toBe(true));
  });

  it.each([
    [409, "invalid_transition"],
    [422, "changed_at_before_last_change"],
  ])(
    "puts the card back where it was when the API answers %i",
    async (status, code) => {
      vi.mocked(applicationStatusChangeService.create).mockRejectedValue(
        new ApiError(status, "rejected", code),
      );
      const { hook, board } = setup();

      act(() => {
        hook.result.current.mutate({
          cardId: "app-1",
          from: "applied",
          to: "screening",
        });
      });

      await waitFor(() => expect(hook.result.current.isError).toBe(true));
      expect(board()).toEqual(BOARD);
    },
  );

  it("sends a plain status change dated now and without a note, then refreshes the board", async () => {
    vi.mocked(applicationStatusChangeService.create).mockResolvedValue(
      {} as Awaited<ReturnType<typeof applicationStatusChangeService.create>>,
    );
    const { hook, queryClient, key } = setup();

    act(() => {
      hook.result.current.mutate({
        cardId: "app-1",
        from: "applied",
        to: "screening",
      });
    });

    await waitFor(() => expect(hook.result.current.isSuccess).toBe(true));
    expect(applicationStatusChangeService.create).toHaveBeenCalledWith("app-1", {
      to_status: "screening",
      changed_at: null,
      note: "",
    });
    await waitFor(() =>
      expect(queryClient.getQueryState(key)?.isInvalidated).toBe(true),
    );
  });
});
