import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import i18n from "@/shared/i18n/i18n";
import { eventsByDay, visibleRange } from "../lib/calendar";
import type { CalendarEvent } from "../types/Calendar";
import { CalendarEventItem } from "./CalendarEventItem";
import { MonthView, WeekView } from "./CalendarViews";

const ZONE = "Europe/Madrid";
const application = {
  id: "app-1",
  position_title: "Backend Developer",
  company: { id: "c-1", name: "Acme" },
};

const reminder = (id: string, starts_at: string, fields: Partial<CalendarEvent> = {}) =>
  ({
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
    ...fields,
  }) satisfies CalendarEvent;

const interview = (id: string, starts_at: string, fields: Partial<CalendarEvent> = {}) =>
  ({
    kind: "interview",
    id,
    starts_at,
    duration_minutes: 60,
    title: null,
    interview_type: "technical",
    format: "online",
    interviewers: "Ana",
    outcome: "pending",
    application,
    ...fields,
  }) satisfies CalendarEvent;

/** El grupo (celda o sección) de un día, por su etiqueta para lectores de pantalla. */
function dayCell(label: RegExp): HTMLElement {
  const marker = screen.getAllByText(label)[0];
  return marker.closest("li") as HTMLElement;
}

beforeAll(async () => {
  await i18n.changeLanguage("es");
});

afterEach(() => {
  cleanup();
});

describe("MonthView", () => {
  const params = { view: "month", date: "2026-10-15" } as const;
  const range = visibleRange(params, ZONE);

  function renderMonth(events: CalendarEvent[], onShowDay = vi.fn()) {
    render(
      <MemoryRouter>
        <MonthView
          days={range.days}
          today="2026-10-01"
          byDay={eventsByDay(events, ZONE)}
          zone={ZONE}
          month={params.date}
          onShowDay={onShowDay}
        />
      </MemoryRouter>,
    );
    // La rejilla (la agenda del móvil se pinta también: jsdom no aplica `md:`).
    return screen.getAllByRole("list")[0];
  }

  it("enseña tres eventos por día y un botón con los que faltan, que abre ese día", async () => {
    const events = Array.from({ length: 5 }, (_, i) =>
      reminder(`r${i}`, `2026-10-14T${String(i + 6).padStart(2, "0")}:00:00Z`),
    );
    const onShowDay = vi.fn();
    const grid = renderMonth(events, onShowDay);
    const cell = within(grid).getByText(/14 de octubre: 5 eventos/).closest("li") as HTMLElement;

    expect(within(cell).getAllByRole("link")).toHaveLength(3);
    await userEvent.click(within(cell).getByRole("button", { name: "2 más" }));

    expect(onShowDay).toHaveBeenCalledWith("2026-10-14");
  });

  it("con tres eventos justos no hay botón de más", () => {
    const events = Array.from({ length: 3 }, (_, i) =>
      reminder(`r${i}`, `2026-10-14T${String(i + 6).padStart(2, "0")}:00:00Z`),
    );
    const grid = renderMonth(events);

    expect(within(grid).queryByRole("button", { name: /más/ })).not.toBeInTheDocument();
  });

  it("pinta un evento en el día de la zona de la cuenta, no en el de UTC", () => {
    // 22:30 UTC del 14 = 00:30 del 15 en Madrid.
    const grid = renderMonth([reminder("late", "2026-10-14T22:30:00Z")]);

    expect(within(grid).getByText(/15 de octubre: 1 evento$/)).toBeInTheDocument();
    expect(within(grid).getByText(/14 de octubre: sin eventos/)).toBeInTheDocument();
    expect(within(grid).getByRole("link")).toHaveAccessibleName(/^00:30, /);
  });

  it("la agenda del móvil solo lista los días del mes con algo, sin menú en la rejilla", () => {
    renderMonth([
      reminder("in", "2026-10-20T08:00:00Z"),
      reminder("out", "2026-09-29T08:00:00Z"), // día de septiembre visible en la rejilla
    ]);
    const [grid, agenda] = screen.getAllByRole("list", { hidden: false }).filter(
      (list) => list.tagName === "OL",
    );

    expect(within(agenda).getAllByRole("link")).toHaveLength(1);
    expect(within(agenda).getByRole("link")).toHaveAccessibleName(/Recordatorio in/);
    // La celda del mes no lleva el menú (no cabe); la agenda sí.
    expect(
      within(grid).queryByRole("button", { name: i18n.t("calendar.add.menu") }),
    ).not.toBeInTheDocument();
    expect(
      within(agenda).getByRole("button", { name: i18n.t("calendar.add.menu") }),
    ).toBeInTheDocument();
    // El evento de septiembre sigue en la rejilla, en su celda.
    expect(within(grid).getByText(/29 de septiembre: 1 evento$/)).toBeInTheDocument();
  });
});

describe("WeekView", () => {
  const range = visibleRange({ view: "week", date: "2026-10-14" }, ZONE);

  function renderWeek(events: CalendarEvent[]) {
    render(
      <MemoryRouter>
        <WeekView days={range.days} today="2026-10-14" byDay={eventsByDay(events, ZONE)} zone={ZONE} />
      </MemoryRouter>,
    );
  }

  it("enseña todos los eventos del día, sin recortar, cada uno con su menú", () => {
    renderWeek(
      Array.from({ length: 6 }, (_, i) => reminder(`r${i}`, `2026-10-14T${String(i + 6).padStart(2, "0")}:00:00Z`)),
    );
    const cell = dayCell(/14 de octubre: 6 eventos/);

    expect(within(cell).getAllByRole("link")).toHaveLength(6);
    expect(within(cell).getAllByRole("button", { name: i18n.t("calendar.add.menu") })).toHaveLength(6);
    expect(screen.queryByRole("button", { name: /más/ })).not.toBeInTheDocument();
  });

  it("los días sin nada lo dicen", () => {
    renderWeek([]);

    expect(screen.getAllByText(i18n.t("calendar.noEvents"))).toHaveLength(7);
  });
});

describe("CalendarEventItem", () => {
  function renderItem(event: CalendarEvent) {
    render(
      <MemoryRouter>
        <CalendarEventItem event={event} zone={ZONE} />
      </MemoryRouter>,
    );
    return screen.getByRole("link");
  }

  it("una entrevista enlaza a su solicitud y nombra puesto, empresa y tipo", () => {
    const link = renderItem(interview("i1", "2026-10-14T07:30:00Z"));

    expect(link).toHaveAttribute("href", "/applications/app-1");
    expect(link).toHaveAccessibleName("09:30, Entrevista: Backend Developer, Técnica, Acme");
  });

  it("un recordatorio ligado enlaza a su solicitud; uno suelto, a Recordatorios", () => {
    const linked = renderItem(
      reminder("r1", "2099-10-14T07:30:00Z", { application, title: "Enviar test" }),
    );
    expect(linked).toHaveAttribute("href", "/applications/app-1");
    expect(linked).toHaveAccessibleName("09:30, Enviar test, Backend Developer · Acme");
    cleanup();

    expect(renderItem(reminder("r2", "2099-10-14T07:30:00Z"))).toHaveAttribute("href", "/reminders");
  });

  it("un recordatorio pasado se marca como vencido; una entrevista pasada, no", () => {
    expect(renderItem(reminder("r1", "2020-01-01T10:00:00Z"))).toHaveAccessibleName(/Vencido$/);
    cleanup();
    expect(renderItem(interview("i1", "2020-01-01T10:00:00Z"))).not.toHaveAccessibleName(
      /Vencido/,
    );
  });

  it("enseña el resultado de una entrevista ya hecha", () => {
    expect(renderItem(interview("i1", "2026-10-14T07:30:00Z", { outcome: "passed" }))).toHaveAccessibleName(
      new RegExp(`, ${i18n.t("interviews.outcome.passed")}$`),
    );
  });
});
