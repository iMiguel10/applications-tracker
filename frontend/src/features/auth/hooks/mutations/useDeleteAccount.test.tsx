import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { authService } from "../../services/auth.service";
import { useDeleteAccount } from "./useDeleteAccount";

vi.mock("../../services/auth.service", () => ({
  authService: { deleteAccount: vi.fn(), signOut: vi.fn() },
}));

function setup() {
  const queryClient = new QueryClient();
  queryClient.setQueryData(["auth", "me"], { id: "1", email: "ana@example.com" });
  queryClient.setQueryData(["applications", "list", { page: 1, limit: 10 }], { items: [] });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
  const { result } = renderHook(() => useDeleteAccount(), { wrapper });
  return { queryClient, result };
}

describe("useDeleteAccount", () => {
  beforeEach(() => vi.clearAllMocks());

  it("deletes the account, then signs out and clears every cached query (T8)", async () => {
    const calls: string[] = [];
    vi.mocked(authService.deleteAccount).mockImplementation(async () => {
      calls.push("delete");
    });
    vi.mocked(authService.signOut).mockImplementation(async () => {
      calls.push("signOut");
    });
    const { queryClient, result } = setup();

    result.current.mutate();

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(calls).toEqual(["delete", "signOut"]);
    expect(queryClient.getQueryCache().getAll()).toHaveLength(0);
  });

  it("still succeeds if signing out fails after the account is gone", async () => {
    vi.mocked(authService.deleteAccount).mockResolvedValue(undefined);
    vi.mocked(authService.signOut).mockRejectedValue(new Error("401"));
    const { result } = setup();

    result.current.mutate();

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it("does not sign out when the deletion fails", async () => {
    vi.mocked(authService.deleteAccount).mockRejectedValue(new Error("500"));
    const { queryClient, result } = setup();

    result.current.mutate();

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(authService.signOut).not.toHaveBeenCalled();
    expect(queryClient.getQueryCache().getAll()).not.toHaveLength(0);
  });
});
