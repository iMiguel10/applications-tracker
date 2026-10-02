import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import i18n from "@/shared/i18n/i18n";
import type { Application } from "@/features/applications/types/Application";
import { InterviewsSection } from "@/features/interviews/components/InterviewsSection";
import { interviewService } from "@/features/interviews/services/interview.service";
import type { Interview } from "@/features/interviews/types/Interview";
import { RemindersList } from "@/features/reminders/components/RemindersList";
import type { Reminder, ReminderStatus } from "@/features/reminders/types/Reminder";

/**
 * Dónde aparece el menú «Añadir al calendario» fuera de la página Calendario
 * (0016): en las entrevistas salvo las canceladas, y solo en los recordatorios
 * pendientes. Lo que ya no va a ocurrir no se lleva a otro calendario.
 */

vi.mock("@/features/interviews/services/interview.service", () => ({
  interviewService: { list: vi.fn() },
}));

const MENU = () => i18n.t("calendar.add.menu");

function wrap(children: ReactNode) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

const application = {
  id: "app-1",
  position_title: "Backend Developer",
  company: { id: "c-1", name: "Acme" },
  allowed_transitions: [],
} as unknown as Application;

const interview = (id: string, outcome: Interview["outcome"]): Interview => ({
  id,
  scheduled_at: "2026-10-05T08:00:00Z",
  duration_minutes: 30,
  interviewers: null,
  interview_type: "technical",
  format: "online",
  outcome,
  notes: null,
  created_at: "2026-10-01T08:00:00Z",
  updated_at: "2026-10-01T08:00:00Z",
});

const reminder = (id: string, status: ReminderStatus): Reminder => ({
  id,
  title: `Recordatorio ${status}`,
  due_at: "2026-10-06T16:30:00Z",
  application: null,
  sent_at: null,
  completed_at: status === "pending" ? null : "2026-10-06T17:00:00Z",
  channel: "in_app",
  status,
  created_at: "2026-10-01T08:00:00Z",
  updated_at: "2026-10-01T08:00:00Z",
});

beforeAll(async () => {
  await i18n.changeLanguage("es");
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("InterviewsSection", () => {
  it("ofrece el menú en cada entrevista salvo en las canceladas", async () => {
    vi.mocked(interviewService.list).mockResolvedValue([
      interview("pending", "pending"),
      interview("passed", "passed"),
      interview("cancelled", "cancelled"),
    ]);

    render(wrap(<InterviewsSection application={application} onSuggestInterviewing={() => {}} />));

    const items = await screen.findAllByRole("listitem");
    expect(items).toHaveLength(3);
    const withMenu = items.map((item) => !!within(item).queryByRole("button", { name: MENU() }));
    const cancelledIndex = items.findIndex((item) =>
      within(item).queryByText(i18n.t("interviews.outcome.cancelled")),
    );
    expect(cancelledIndex).toBeGreaterThanOrEqual(0);
    expect(withMenu.filter(Boolean)).toHaveLength(2);
    expect(withMenu[cancelledIndex]).toBe(false);
  });
});

describe("RemindersList", () => {
  it("solo los recordatorios pendientes llevan el menú", () => {
    render(
      wrap(
        <RemindersList
          reminders={[reminder("p", "pending"), reminder("d", "done"), reminder("x", "dismissed")]}
        />,
      ),
    );

    const item = (status: ReminderStatus) =>
      screen.getByText(`Recordatorio ${status}`).closest("li") as HTMLElement;
    expect(within(item("pending")).getByRole("button", { name: MENU() })).toBeInTheDocument();
    expect(within(item("done")).queryByRole("button", { name: MENU() })).not.toBeInTheDocument();
    expect(within(item("dismissed")).queryByRole("button", { name: MENU() })).not.toBeInTheDocument();
  });
});
