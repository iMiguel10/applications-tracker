import { beforeAll, describe, expect, it } from "vitest";

import i18n from "@/shared/i18n/i18n";
import type { Interview } from "@/features/interviews/types/Interview";
import type { CalendarEvent } from "../types/Calendar";
import {
  buildIcs,
  entryFromEvent,
  entryFromInterview,
  googleCalendarUrl,
  icsFilename,
  type CalendarEntry,
} from "./addToCalendar";

/**
 * Pruebas adversas del `.ics` y del enlace de Google (QA de F17, RF-133): escape y
 * plegado RFC 5545 con caracteres multibyte, títulos vacíos o maliciosos y notas
 * que nunca salen.
 */

const ORIGIN = "https://tracker.example";
const NOW = new Date("2026-10-01T12:00:00Z");
const t = i18n.t.bind(i18n);
const encoder = new TextEncoder();

const base: CalendarEntry = {
  uid: "reminder-r1@applications-tracker",
  title: "Llamar",
  start: new Date("2026-10-05T08:00:00Z"),
  end: new Date("2026-10-05T08:15:00Z"),
  details: [],
  url: `${ORIGIN}/reminders`,
};

const application = {
  id: "app-1",
  position_title: "Backend Developer",
  company: { id: "c-1", name: "Acme" },
};

const unfold = (ics: string) => ics.replace(/\r\n /g, "").split("\r\n");
const physicalLines = (ics: string) => ics.split("\r\n").slice(0, -1);
const property = (ics: string, name: string) =>
  unfold(ics).filter((line) => line.startsWith(`${name}:`));

/** Un surrogate suelto: un carácter fuera del plano básico partido por la mitad. */
const LONE_SURROGATE = /[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/;

beforeAll(async () => {
  await i18n.changeLanguage("es");
});

describe("plegado a 75 octetos con caracteres multibyte", () => {
  it.each([
    ["emojis de 4 octetos", "🎉".repeat(60)],
    ["emojis compuestos (ZWJ y modificadores)", "👩‍💻👨‍👩‍👧‍👦👍🏽".repeat(12)],
    ["CJK de 3 octetos", "面接の準備をする".repeat(15)],
    ["mezcla con un desfase de 1 octeto", `x${"ñ€🎉".repeat(30)}`],
    ["mezcla con un desfase de 2 octetos", `xy${"ñ€🎉".repeat(30)}`],
  ])("%s: ninguna línea pasa de 75 octetos y el texto vuelve entero", (_, title) => {
    const ics = buildIcs({ ...base, title }, NOW);

    for (const line of physicalLines(ics)) {
      expect(encoder.encode(line).length).toBeLessThanOrEqual(75);
      expect(line).not.toMatch(LONE_SURROGATE);
    }
    expect(property(ics, "SUMMARY")).toEqual([`SUMMARY:${title}`]);
  });

  it("cada línea de continuación empieza por un único espacio", () => {
    const ics = buildIcs({ ...base, title: "a".repeat(300) }, NOW);
    const lines = physicalLines(ics);
    const at = lines.findIndex((line) => line.startsWith("SUMMARY:"));
    const next = lines.findIndex((line, i) => i > at && line.startsWith("DESCRIPTION:"));
    const continuations = lines.slice(at + 1, next);

    expect(continuations.length).toBeGreaterThan(1);
    for (const continuation of continuations) {
      expect(continuation).toMatch(/^ a+$/);
    }
    expect(continuations.map((line) => line.slice(1)).join("")).toHaveLength(300 - 67);
  });

  it("una línea de 75 octetos exactos no se pliega; una de 76, sí", () => {
    // "SUMMARY:" ocupa 8 octetos.
    const exact = buildIcs({ ...base, title: "a".repeat(67) }, NOW);
    const over = buildIcs({ ...base, title: "a".repeat(68) }, NOW);

    expect(physicalLines(exact)).toContain(`SUMMARY:${"a".repeat(67)}`);
    expect(physicalLines(over)).not.toContain(`SUMMARY:${"a".repeat(68)}`);
    expect(property(over, "SUMMARY")).toEqual([`SUMMARY:${"a".repeat(68)}`]);
  });

  it("un carácter de 4 octetos que no cabe al final pasa entero a la línea siguiente", () => {
    // 8 + 66 = 74 octetos: el emoji (4) no cabe en el octeto 75.
    const ics = buildIcs({ ...base, title: `${"a".repeat(66)}🎉` }, NOW);
    const lines = physicalLines(ics);
    const at = lines.findIndex((line) => line.startsWith("SUMMARY:"));

    expect(lines[at]).toBe(`SUMMARY:${"a".repeat(66)}`);
    expect(lines[at + 1]).toBe(" 🎉");
  });
});

describe("escape de texto", () => {
  it("un título con saltos de línea no puede inyectar propiedades ni otro evento", () => {
    const title = "Hola\r\nEND:VEVENT\nBEGIN:VEVENT\nSUMMARY:falso";
    const ics = buildIcs({ ...base, title }, NOW);
    const lines = unfold(ics);

    expect(lines.filter((line) => line === "BEGIN:VEVENT")).toHaveLength(1);
    expect(lines.filter((line) => line === "END:VEVENT")).toHaveLength(1);
    expect(lines.filter((line) => line.startsWith("SUMMARY:"))).toHaveLength(1);
    // Ningún CR ni LF sueltos: solo los CRLF que separan líneas.
    expect(ics.replace(/\r\n/g, "")).not.toMatch(/[\r\n]/);
  });

  it("un retorno de carro suelto tampoco queda en crudo (la API lo acepta en un título)", () => {
    // RFC 5545 §3.3.11: TEXT no admite caracteres de control; un lector que tome
    // el CR suelto como fin de línea leería ATTACH como otra propiedad del evento.
    const ics = buildIcs({ ...base, title: "Llamar\rATTACH:http://evil.example/x" }, NOW);

    expect(ics.replace(/\r\n/g, "")).not.toContain("\r");
  });

  it("escapa la barra antes que lo demás (sin dobles escapes)", () => {
    const ics = buildIcs({ ...base, title: "a\\;b,c\\n" }, NOW);

    expect(property(ics, "SUMMARY")).toEqual(["SUMMARY:a\\\\\\;b\\,c\\\\n"]);
  });

  it("los dos puntos no se escapan (RFC 5545 §3.3.11)", () => {
    const ics = buildIcs({ ...base, title: "Entrevista: 10:00" }, NOW);

    expect(property(ics, "SUMMARY")).toEqual(["SUMMARY:Entrevista: 10:00"]);
  });

  it("los entrevistadores con saltos de línea y comas van escapados en la descripción", () => {
    const entry = entryFromEvent(
      {
        kind: "interview",
        id: "i1",
        starts_at: "2026-10-05T08:00:00Z",
        duration_minutes: 30,
        title: null,
        interview_type: null,
        format: null,
        interviewers: "Ana, CTO\nLuis; RR. HH.",
        outcome: "pending",
        application,
      },
      t,
      ORIGIN,
    );
    const [description] = property(buildIcs(entry, NOW), "DESCRIPTION");

    expect(description).toBe(
      `DESCRIPTION:Con quién: Ana\\, CTO\\nLuis\\; RR. HH.\\n${ORIGIN}/applications/app-1`,
    );
  });
});

describe("títulos vacíos", () => {
  const empty: CalendarEvent = {
    kind: "reminder",
    id: "r1",
    starts_at: "2026-10-05T08:00:00Z",
    duration_minutes: null,
    title: null,
    interview_type: null,
    format: null,
    interviewers: null,
    outcome: null,
    application: null,
  };

  it("un recordatorio sin título sigue dando un .ics válido y un nombre de fichero", () => {
    const entry = entryFromEvent(empty, t, ORIGIN);
    const ics = buildIcs(entry, NOW);

    expect(property(ics, "SUMMARY")).toEqual(["SUMMARY:"]);
    expect(property(ics, "UID")).toEqual(["UID:reminder-r1@applications-tracker"]);
    expect(icsFilename(entry)).toMatch(/^evento-2026-10-0[45]\.ics$/);
  });

  it("y el enlace de Google lleva el texto vacío, sin romper los demás parámetros", () => {
    const url = new URL(googleCalendarUrl(entryFromEvent(empty, t, ORIGIN)));

    expect(url.searchParams.get("text")).toBe("");
    expect(url.searchParams.get("dates")).toBe("20261005T080000Z/20261005T081500Z");
  });
});

describe("enlace de Google", () => {
  it("un título con & # = y + llega intacto como un solo parámetro", () => {
    const title = "R&D #1 = C++ ¿sí? 50% 🎉";
    const url = new URL(googleCalendarUrl({ ...base, title }));

    expect(url.origin + url.pathname).toBe("https://calendar.google.com/calendar/render");
    expect(url.searchParams.get("action")).toBe("TEMPLATE");
    expect(url.searchParams.get("text")).toBe(title);
    expect([...url.searchParams.keys()].sort()).toEqual(["action", "dates", "details", "text"]);
  });
});

describe("notas, nunca", () => {
  const SECRET = "NOTA-PRIVADA-7f3a";

  it("ni la entrevista del detalle ni su evento del calendario llevan las notas", () => {
    const interview: Interview = {
      id: "int-1",
      scheduled_at: "2026-10-05T08:00:00Z",
      duration_minutes: 45,
      interviewers: "Ana",
      interview_type: "technical",
      format: "online",
      outcome: "pending",
      notes: SECRET,
      created_at: "2026-10-01T08:00:00Z",
      updated_at: "2026-10-01T08:00:00Z",
    };
    // Un evento al que la API añadiera notas por error tampoco las pasa.
    const leaky = {
      kind: "interview",
      id: "int-1",
      starts_at: interview.scheduled_at,
      duration_minutes: 45,
      title: null,
      interview_type: "technical",
      format: "online",
      interviewers: "Ana",
      outcome: "pending",
      application,
      notes: SECRET,
    } as CalendarEvent;

    for (const entry of [
      entryFromInterview(interview, application, t, ORIGIN),
      entryFromEvent(leaky, t, ORIGIN),
    ]) {
      expect(JSON.stringify(entry)).not.toContain(SECRET);
      expect(buildIcs(entry, NOW)).not.toContain(SECRET);
      expect(decodeURIComponent(googleCalendarUrl(entry))).not.toContain(SECRET);
    }
  });
});

describe("horas", () => {
  it("la duración se cuenta en tiempo real aunque cruce un cambio de hora", () => {
    // Madrid, 25 de octubre de 2026: a las 03:00 CEST vuelven a ser las 02:00.
    const entry = entryFromEvent(
      {
        kind: "interview",
        id: "i1",
        starts_at: "2026-10-25T00:30:00Z", // 02:30 CEST
        duration_minutes: 90,
        title: null,
        interview_type: null,
        format: null,
        interviewers: null,
        outcome: "pending",
        application,
      },
      t,
      ORIGIN,
    );
    const lines = unfold(buildIcs(entry, NOW));

    expect(lines).toContain("DTSTART:20261025T003000Z");
    expect(lines).toContain("DTEND:20261025T020000Z");
  });
});
