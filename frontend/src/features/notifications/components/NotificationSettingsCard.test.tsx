import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import i18n from "@/shared/i18n/i18n";
import { authKeys } from "@/features/auth/auth.keys";
import type { Preferences } from "@/features/auth/types/Auth";
import { authService } from "@/features/auth/services/auth.service";
import { metaService } from "@/features/meta/services/meta.service";
import { notificationSettingsService } from "../services/notificationSettings.service";
import { NotificationSettingsCard } from "./NotificationSettingsCard";

vi.mock("@/features/meta/services/meta.service", () => ({
  metaService: { get: vi.fn() },
}));
vi.mock("@/features/auth/services/auth.service", () => ({
  authService: { isEmailVerified: vi.fn() },
}));
vi.mock("../services/notificationSettings.service", () => ({
  notificationSettingsService: { update: vi.fn() },
}));

const PREFERENCES: Preferences = {
  language: null,
  stale_after_days: 14,
  timezone: "Europe/Madrid",
  notify_reminder_due: true,
  notify_interview: true,
  notify_weekly_digest: false,
  notify_stale: false,
  interview_notice_hours: 24,
};

function renderCard({
  emailEnabled = true,
  verified = true,
  preferences = PREFERENCES,
}: { emailEnabled?: boolean; verified?: boolean; preferences?: Preferences } = {}) {
  vi.mocked(metaService.get).mockResolvedValue({ email_enabled: emailEnabled });
  vi.mocked(authService.isEmailVerified).mockResolvedValue(verified);
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  queryClient.setQueryData(authKeys.preferences(), preferences);
  render(
    <QueryClientProvider client={queryClient}>
      <NotificationSettingsCard preferences={preferences} />
    </QueryClientProvider>,
  );
  return queryClient;
}

const toggle = (key: string) =>
  screen.getByRole("switch", { name: new RegExp(i18n.t(`notifications.${key}.label`)) });

describe("NotificationSettingsCard", () => {
  beforeAll(async () => {
    await i18n.changeLanguage("es");
  });
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("saves only the switch that changed, right away", async () => {
    vi.mocked(notificationSettingsService.update).mockResolvedValue({
      ...PREFERENCES,
      notify_weekly_digest: true,
    });
    const queryClient = renderCard();

    await userEvent.click(toggle("notify_weekly_digest"));

    expect(notificationSettingsService.update).toHaveBeenCalledWith({
      notify_weekly_digest: true,
    });
    expect(queryClient.getQueryData<Preferences>(authKeys.preferences())).toMatchObject({
      notify_weekly_digest: true,
    });
  });

  it("puts the switch back when saving fails", async () => {
    vi.mocked(notificationSettingsService.update).mockRejectedValue(new Error("boom"));
    const queryClient = renderCard();

    await userEvent.click(toggle("notify_reminder_due"));

    await vi.waitFor(() =>
      expect(queryClient.getQueryData<Preferences>(authKeys.preferences())).toMatchObject({
        notify_reminder_due: true,
      }),
    );
  });

  it("offers the interview notice only while that notification is on", () => {
    renderCard();
    expect(screen.getByText(i18n.t("notifications.noticeLabel"))).toBeInTheDocument();
    cleanup();

    renderCard({ preferences: { ...PREFERENCES, notify_interview: false } });
    expect(screen.queryByText(i18n.t("notifications.noticeLabel"))).not.toBeInTheDocument();
  });

  it("explains and locks the switches when the installation sends no email", async () => {
    renderCard({ emailEnabled: false });

    expect(await screen.findByText(i18n.t("notifications.unavailable"))).toBeInTheDocument();
    expect(toggle("notify_reminder_due")).toHaveAttribute("aria-disabled", "true");
  });

  it("warns that notifications need a verified email", async () => {
    renderCard({ verified: false });

    expect(await screen.findByText(i18n.t("notifications.unverified"))).toBeInTheDocument();
  });
});
