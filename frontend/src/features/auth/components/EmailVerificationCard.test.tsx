import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import i18n from "@/shared/i18n/i18n";
import { metaService } from "@/features/meta/services/meta.service";
import { authService } from "../services/auth.service";
import { EmailVerificationCard } from "./EmailVerificationCard";

vi.mock("@/features/meta/services/meta.service", () => ({
  metaService: { get: vi.fn() },
}));
vi.mock("../services/auth.service", () => ({
  authService: { isEmailVerified: vi.fn(), sendVerificationEmail: vi.fn() },
}));

const EMAIL = "ana@example.com";

function renderCard({ emailEnabled, verified }: { emailEnabled: boolean; verified: boolean }) {
  vi.mocked(metaService.get).mockResolvedValue({ email_enabled: emailEnabled });
  vi.mocked(authService.isEmailVerified).mockResolvedValue(verified);
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <EmailVerificationCard email={EMAIL} />
    </QueryClientProvider>,
  );
}

const resendButton = () => screen.queryByRole("button", { name: i18n.t("auth.verifyEmail.resend") });

describe("EmailVerificationCard", () => {
  beforeAll(async () => {
    await i18n.changeLanguage("es");
  });
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("shows a verified email without offering to resend", async () => {
    renderCard({ emailEnabled: true, verified: true });

    expect(await screen.findByText(i18n.t("account.email.verified"))).toBeInTheDocument();
    expect(screen.getByText(EMAIL)).toBeInTheDocument();
    expect(resendButton()).not.toBeInTheDocument();
  });

  it("offers to resend the link while the email is not verified", async () => {
    vi.mocked(authService.sendVerificationEmail).mockResolvedValue("ok");
    renderCard({ emailEnabled: true, verified: false });

    expect(await screen.findByText(i18n.t("account.email.unverified"))).toBeInTheDocument();
    await userEvent.click(resendButton()!);

    expect(
      await screen.findByText(i18n.t("auth.verifyEmail.bannerResent", { email: EMAIL })),
    ).toBeInTheDocument();
  });

  it("explains, instead of offering to resend, when the installation sends no email", async () => {
    renderCard({ emailEnabled: false, verified: false });

    expect(await screen.findByText(i18n.t("account.email.unavailable"))).toBeInTheDocument();
    expect(resendButton()).not.toBeInTheDocument();
  });
});
