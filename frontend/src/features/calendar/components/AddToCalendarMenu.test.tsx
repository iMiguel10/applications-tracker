import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import i18n from "@/shared/i18n/i18n";
import { downloadBlob } from "@/shared/lib/download";
import type { CalendarEntry } from "../lib/addToCalendar";
import { AddToCalendarMenu } from "./AddToCalendarMenu";

vi.mock("@/shared/lib/download", () => ({ downloadBlob: vi.fn() }));

const entry: CalendarEntry = {
  uid: "interview-int-1@applications-tracker",
  title: "Entrevista: Backend Developer — Acme",
  start: new Date("2026-10-05T08:00:00Z"),
  end: new Date("2026-10-05T08:45:00Z"),
  details: ["Tipo: Técnica"],
  url: "http://localhost/applications/app-1",
};

async function openMenu() {
  const user = userEvent.setup();
  render(<AddToCalendarMenu entry={entry} />);
  await user.click(screen.getByRole("button", { name: i18n.t("calendar.add.menu") }));
  return user;
}

beforeAll(async () => {
  await i18n.changeLanguage("es");
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.mocked(downloadBlob).mockClear();
});

describe("AddToCalendarMenu", () => {
  it("ofrece Google Calendar y la descarga del .ics", async () => {
    await openMenu();

    const items = await screen.findAllByRole("menuitem");
    expect(items.map((item) => item.textContent)).toEqual([
      i18n.t("calendar.add.google"),
      i18n.t("calendar.add.ics"),
    ]);
  });

  it("abre Google Calendar en otra pestaña, sin darle acceso a la app", async () => {
    const open = vi.spyOn(window, "open").mockReturnValue(null);
    const user = await openMenu();

    await user.click(await screen.findByRole("menuitem", { name: i18n.t("calendar.add.google") }));

    expect(open).toHaveBeenCalledOnce();
    const [url, target, features] = open.mock.calls[0];
    expect(String(url)).toMatch(/^https:\/\/calendar\.google\.com\/calendar\/render\?/);
    expect(target).toBe("_blank");
    expect(features).toBe("noopener,noreferrer");
  });

  it("descarga el .ics con su nombre", async () => {
    const user = await openMenu();

    await user.click(await screen.findByRole("menuitem", { name: i18n.t("calendar.add.ics") }));

    expect(downloadBlob).toHaveBeenCalledOnce();
    const [blob, filename] = vi.mocked(downloadBlob).mock.calls[0];
    expect(filename).toBe("entrevista-backend-developer-acme-2026-10-05.ics");
    expect(blob.type).toBe("text/calendar;charset=utf-8");
    expect(await blob.text()).toContain("UID:interview-int-1@applications-tracker");
  });
});
