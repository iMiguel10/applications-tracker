import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { useSignOut } from "./useSignOut";

vi.mock("../../services/auth.service", () => ({
  authService: { signOut: vi.fn().mockResolvedValue(undefined) },
}));

describe("useSignOut", () => {
  it("clears every cached query so the next user cannot see previous data (T8)", async () => {
    const queryClient = new QueryClient();
    queryClient.setQueryData(["auth", "me"], { id: "1", email: "ana@example.com" });
    queryClient.setQueryData(["applications", "list", { page: 1, limit: 10 }], { items: [] });

    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>{children}</MemoryRouter>
      </QueryClientProvider>
    );

    const { result } = renderHook(() => useSignOut(), { wrapper });
    result.current.mutate();

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(queryClient.getQueryCache().getAll()).toHaveLength(0);
  });
});
