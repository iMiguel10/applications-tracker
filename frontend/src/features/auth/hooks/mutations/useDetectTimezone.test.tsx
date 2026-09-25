import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { preferencesService } from "../../services/preferences.service";
import type { Preferences } from "../../types/Auth";
import { useDetectTimezone } from "./useDetectTimezone";

vi.mock("../../services/preferences.service", () => ({
  preferencesService: { setTimezone: vi.fn() },
}));
vi.mock("../../lib/timezones", () => ({ browserTimezone: () => "America/Mexico_City" }));

const BASE: Preferences = { language: null, stale_after_days: 14, timezone: null };

function renderWith(preferences: Preferences | undefined) {
  const queryClient = new QueryClient();
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return renderHook(({ prefs }) => useDetectTimezone(prefs), {
    wrapper,
    initialProps: { prefs: preferences },
  });
}

describe("useDetectTimezone", () => {
  afterEach(() => vi.clearAllMocks());

  it("sends the browser time zone once when the account has none (RF-07)", async () => {
    vi.mocked(preferencesService.setTimezone).mockResolvedValue({
      ...BASE,
      timezone: "America/Mexico_City",
    });
    const { rerender } = renderWith(BASE);

    await waitFor(() => expect(preferencesService.setTimezone).toHaveBeenCalled());
    expect(vi.mocked(preferencesService.setTimezone).mock.calls[0][0]).toBe("America/Mexico_City");
    // Un segundo render con la zona aún vacía no repite la petición.
    rerender({ prefs: { ...BASE } });
    expect(preferencesService.setTimezone).toHaveBeenCalledOnce();
  });

  it("never overrides a time zone the account already has", () => {
    renderWith({ ...BASE, timezone: "Europe/Madrid" });

    expect(preferencesService.setTimezone).not.toHaveBeenCalled();
  });

  it("waits until the preferences are loaded", () => {
    renderWith(undefined);

    expect(preferencesService.setTimezone).not.toHaveBeenCalled();
  });
});
