import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import i18n from "@/shared/i18n/i18n";
import { metaService } from "@/features/meta/services/meta.service";
import { authService } from "../services/auth.service";
import { EmailVerificationBanner } from "./EmailVerificationBanner";

vi.mock("@/features/meta/services/meta.service", () => ({
  metaService: { get: vi.fn() },
}));
vi.mock("../services/auth.service", () => ({
  authService: { isEmailVerified: vi.fn(), sendVerificationEmail: vi.fn() },
}));

const EMAIL = "ana@example.com";

function renderBanner({ emailEnabled, verified }: { emailEnabled: boolean; verified: boolean }) {
  vi.mocked(metaService.get).mockResolvedValue({ email_enabled: emailEnabled });
  vi.mocked(authService.isEmailVerified).mockResolvedValue(verified);
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <EmailVerificationBanner email={EMAIL} />
    </QueryClientProvider>,
  );
}

describe("EmailVerificationBanner", () => {
  beforeAll(async () => {
    await i18n.changeLanguage("es");
  });
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("reminds an unverified user and resends the link (RF-05)", async () => {
    vi.mocked(authService.sendVerificationEmail).mockResolvedValue("ok");
    renderBanner({ emailEnabled: true, verified: false });

    expect(await screen.findByText(i18n.t("auth.verifyEmail.banner", { email: EMAIL }))).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: i18n.t("auth.verifyEmail.resend") }));

    expect(
      await screen.findByText(i18n.t("auth.verifyEmail.bannerResent", { email: EMAIL })),
    ).toBeInTheDocument();
    expect(authService.sendVerificationEmail).toHaveBeenCalledOnce();
  });

  it("shows nothing once the email is verified", async () => {
    renderBanner({ emailEnabled: true, verified: true });

    await vi.waitFor(() => expect(authService.isEmailVerified).toHaveBeenCalled());
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("shows nothing and asks nothing when the installation sends no email", async () => {
    renderBanner({ emailEnabled: false, verified: false });

    await vi.waitFor(() => expect(metaService.get).toHaveBeenCalled());
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(authService.isEmailVerified).not.toHaveBeenCalled();
  });
});
