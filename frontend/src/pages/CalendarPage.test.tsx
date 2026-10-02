import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router-dom";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import i18n from "@/shared/i18n/i18n";
import { preferencesService } from "@/features/auth/services/preferences.service";
import type { Preferences } from "@/features/auth/types/Auth";
import { calendarService } from "@/features/calendar/services/calendar.service";
import type { CalendarEvent } from "@/features/calendar/types/Calendar";
import { CalendarPage } from "./CalendarPage";

vi.mock("@/features/calendar/services/calendar.service", () => ({
  calendarService: { events: vi.fn() },
}));
vi.mock("@/features/auth/services/preferences.service", () => ({
  preferencesService: { get: vi.fn() },
}));

const preferences = (timezone: string | null) => ({ timezone }) as unknown as Preferences;

const reminder = (id: string, starts_at: string): CalendarEvent => ({
  kind: "reminder",
  id,
  starts_at,
  duration_minutes: null,
  title: `Recordatorio ${id}`,
  interview_type: null,
  format: null,
  interviewers: null,
  outcome: null,
  application: null,
});

function Location() {
  const location = useLocation();
  return <output data-testid="location">{location.pathname + location.search}</output>;
}

function renderPage(url: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[url]}>
        <CalendarPage />
        <Location />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("CalendarPage", () => {
  beforeAll(async () => {
    // El navegador, en otra zona que la cuenta.
    vi.stubEnv("TZ", "America/Los_Angeles");
    await i18n.changeLanguage("es");
  });
  afterAll(() => {
    vi.unstubAllEnvs();
  });
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("pide el rango del mes en la zona de la cuenta, no en la del navegador", async () => {
    vi.mocked(preferencesService.get).mockResolvedValue(preferences("Europe/Madrid"));
    vi.mocked(calendarService.events).mockResolvedValue({ events: [] });

    renderPage("/calendar?date=2026-10-15");

    await waitFor(() => expect(calendarService.events).toHaveBeenCalled());
    expect(calendarService.events).toHaveBeenCalledTimes(1);
    expect(calendarService.events).toHaveBeenCalledWith(
      "2026-09-27T22:00:00.000Z",
      "2026-11-01T23:00:00.000Z",
    );
    expect(screen.getByText("Horas en Europe/Madrid")).toBeInTheDocument();
  });

  it("no pide nada hasta tener la zona de la cuenta", async () => {
    vi.mocked(preferencesService.get).mockReturnValue(new Promise(() => {}));
    vi.mocked(calendarService.events).mockResolvedValue({ events: [] });

    renderPage("/calendar?date=2026-10-15");
    await new Promise((resolve) => setTimeout(resolve, 50));

    expect(calendarService.events).not.toHaveBeenCalled();
  });

  it("sin zona en la cuenta, usa la del navegador", async () => {
    vi.mocked(preferencesService.get).mockResolvedValue(preferences(null));
    vi.mocked(calendarService.events).mockResolvedValue({ events: [] });

    renderPage("/calendar?view=week&date=2026-10-15");

    await waitFor(() =>
      expect(calendarService.events).toHaveBeenCalledWith(
        "2026-10-12T07:00:00.000Z",
        "2026-10-19T07:00:00.000Z",
      ),
    );
  });

  it("dice que no hay nada en un mes vacío y en una semana vacía", async () => {
    vi.mocked(preferencesService.get).mockResolvedValue(preferences("Europe/Madrid"));
    vi.mocked(calendarService.events).mockResolvedValue({ events: [] });

    renderPage("/calendar?date=2026-10-15");
    expect(await screen.findByText(i18n.t("calendar.emptyMonth"))).toBeInTheDocument();
    cleanup();

    renderPage("/calendar?view=week&date=2026-10-15");
    expect(await screen.findByText(i18n.t("calendar.emptyWeek"))).toBeInTheDocument();
  });

  it("con eventos no enseña el aviso de vacío", async () => {
    vi.mocked(preferencesService.get).mockResolvedValue(preferences("Europe/Madrid"));
    vi.mocked(calendarService.events).mockResolvedValue({
      events: [reminder("r1", "2026-10-14T08:00:00Z")],
    });

    renderPage("/calendar?date=2026-10-15");

    expect((await screen.findAllByRole("link", { name: /Recordatorio r1/ })).length).toBeGreaterThan(0);
    expect(screen.queryByText(i18n.t("calendar.emptyMonth"))).not.toBeInTheDocument();
  });

  it("si la API falla, enseña el error con Reintentar", async () => {
    vi.mocked(preferencesService.get).mockResolvedValue(preferences("Europe/Madrid"));
    vi.mocked(calendarService.events).mockRejectedValue(new Error("boom"));

    renderPage("/calendar?date=2026-10-15");

    const alert = await screen.findByRole("alert");
    expect(within(alert).getByRole("button", { name: /Reintentar/ })).toBeInTheDocument();
  });

  it("“N más” abre la semana de ese día y se navega por semanas", async () => {
    vi.mocked(preferencesService.get).mockResolvedValue(preferences("Europe/Madrid"));
    vi.mocked(calendarService.events).mockResolvedValue({
      events: Array.from({ length: 4 }, (_, i) => reminder(`r${i}`, `2026-10-21T0${i + 6}:00:00Z`)),
    });
    const user = userEvent.setup();

    renderPage("/calendar?date=2026-10-15");
    await user.click(await screen.findByRole("button", { name: "1 más" }));

    expect(screen.getByTestId("location")).toHaveTextContent("/calendar?view=week&date=2026-10-21");
    await user.click(screen.getByRole("button", { name: i18n.t("calendar.nextWeek") }));
    expect(screen.getByTestId("location")).toHaveTextContent("/calendar?view=week&date=2026-10-28");
    await waitFor(() =>
      expect(calendarService.events).toHaveBeenLastCalledWith(
        "2026-10-25T23:00:00.000Z",
        "2026-11-01T23:00:00.000Z",
      ),
    );
  });

  it("una fecha inválida en la URL cae en hoy", async () => {
    vi.mocked(preferencesService.get).mockResolvedValue(preferences("Europe/Madrid"));
    vi.mocked(calendarService.events).mockResolvedValue({ events: [] });

    renderPage("/calendar?date=2026-02-30");

    await waitFor(() => expect(calendarService.events).toHaveBeenCalled());
    const [start, end] = vi.mocked(calendarService.events).mock.calls[0];
    const days = (Date.parse(end) - Date.parse(start)) / 86_400_000;
    expect(days).toBeGreaterThanOrEqual(27);
    expect(days).toBeLessThanOrEqual(43);
  });
});
