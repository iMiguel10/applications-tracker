import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { authService } from "../../services/auth.service";
import { useSubmitNewPassword } from "./useSubmitNewPassword";

vi.mock("../../services/auth.service", () => ({
  authService: {
    submitNewPassword: vi.fn(),
    sessionExists: vi.fn(),
    signOut: vi.fn().mockResolvedValue(undefined),
  },
}));

function setup() {
  const queryClient = new QueryClient();
  queryClient.setQueryData(["auth", "me"], { id: "1", email: "ana@example.com" });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  const { result } = renderHook(() => useSubmitNewPassword(), { wrapper });
  return { queryClient, result };
}

describe("useSubmitNewPassword", () => {
  beforeEach(() => vi.clearAllMocks());

  it("signs out the local session and clears the cache after a reset (T11)", async () => {
    vi.mocked(authService.submitNewPassword).mockResolvedValue({ status: "ok" });
    vi.mocked(authService.sessionExists).mockResolvedValue(true);
    const { queryClient, result } = setup();

    result.current.mutate("nueva-clave-42");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(authService.signOut).toHaveBeenCalledOnce();
    expect(queryClient.getQueryCache().getAll()).toHaveLength(0);
  });

  it("keeps everything when the link is invalid", async () => {
    vi.mocked(authService.submitNewPassword).mockResolvedValue({ status: "invalid_link" });
    vi.mocked(authService.sessionExists).mockResolvedValue(true);
    const { queryClient, result } = setup();

    result.current.mutate("nueva-clave-42");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(authService.signOut).not.toHaveBeenCalled();
    expect(queryClient.getQueryCache().getAll()).toHaveLength(1);
  });
});
