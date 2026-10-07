import { describe, expect, it } from "vitest";

import type { ProfileEntry } from "@/features/profile/types/ProfileEntry";
import type { Requirement } from "../types/Ai";
import { containsKeyword, evidenceLabels, offerMatch, tokenize, type CvSource } from "./match";
import type { ReviewState } from "./review";

const has = (text: string, keyword: string) => containsKeyword(tokenize(text), keyword);

const entry = (fields: Partial<ProfileEntry>): ProfileEntry => ({
  id: "job",
  kind: "experience",
  title: "Backend Developer",
  organization: "Acme",
  location: null,
  start_date: null,
  end_date: null,
  is_current: true,
  description: null,
  bullets: [],
  ...fields,
});

const SOURCE: CvSource = {
  profile: {
    full_name: "Ana",
    headline: "Desarrolladora backend",
    contact_email: null,
    phone: null,
    location: null,
    links: [],
    summary: "Me gusta Postgres",
  },
  entries: [
    entry({
      bullets: [
        { id: "b1", text: "Optimicé consultas en bases de datos relacionales" },
        { id: "b2", text: "Monté la integración continua" },
      ],
    }),
    entry({ id: "old", title: "Camarera", organization: "Bar", bullets: [] }),
    entry({ id: "degree", kind: "education", title: "Ingeniería Informática" }),
  ],
  skills: [
    { id: "s-py", name: "Python", category: null, level: null },
    { id: "s-docker", name: "Docker", category: null, level: null },
  ],
  languages: [{ id: "l-en", language: "Inglés", level: "b2" }],
};

const requirement = (fields: Partial<Requirement>): Requirement => ({
  name: "PostgreSQL",
  importance: "required",
  keywords: ["PostgreSQL"],
  evidence: [],
  note: "",
  ...fields,
});

// La revisión: solo la primera experiencia, con un logro reescrito, y Python.
const reviewed = (bullet: string, skills = ["s-py"]): ReviewState => ({
  summary: "Backend con Python",
  experiences: [
    {
      entryId: "job",
      entry: SOURCE.entries[0],
      bullets: [{ bulletId: "b1", original: "x", text: bullet }],
    },
  ],
  skills: skills.map((id) => ({ id, name: id })),
});

describe("containsKeyword", () => {
  it("ignora mayúsculas, tildes, puntuación y versiones", () => {
    expect(has("Experiencia con PostgreSQL 16.", "postgresql")).toBe(true);
    expect(has("Gestión de proyectos", "gestion de proyectos")).toBe(true);
    expect(has("Python 3.12", "Python 3")).toBe(true);
    expect(has("API REST con FastAPI", "APIs REST")).toBe(true);
    expect(has("Varios servidores", "servidor")).toBe(true);
  });

  it("busca palabras enteras, no trozos", () => {
    expect(has("Trabajé en Google", "Go")).toBe(false);
    expect(has("Java y Go", "Go")).toBe(true);
    expect(has("JavaScript", "Java")).toBe(false);
  });

  it("conserva C++ y C#, y une palabras separadas", () => {
    expect(has("C++ y C#", "C++")).toBe(true);
    expect(has("C y Go", "C++")).toBe(false);
    expect(has("Backend en NodeJS", "Node.js")).toBe(true);
  });
});

describe("offerMatch", () => {
  it("sin requisitos (propuestas de cv/v1) no hay encaje", () => {
    expect(offerMatch(null, reviewed("x"), SOURCE)).toBeNull();
    expect(offerMatch([], reviewed("x"), SOURCE)).toBeNull();
  });

  it("calcula antes y después, y un imprescindible pesa el doble", () => {
    const requirements = [
      requirement({
        name: "PostgreSQL",
        keywords: ["PostgreSQL"],
        evidence: [{ kind: "bullet", id: "b1" }],
      }),
      requirement({
        name: "Kubernetes",
        keywords: ["Kubernetes"],
        importance: "preferred",
      }),
      requirement({ name: "Python", keywords: ["Python"] }),
    ];

    const before = offerMatch(requirements, reviewed("Optimicé consultas"), SOURCE)!;
    // Python (2) de 5: el perfil no dice PostgreSQL sino Postgres.
    expect(before.before).toBe(40);
    expect(before.after).toBe(40);

    // Al nombrarlo en el logro revisado, sube al momento.
    const after = offerMatch(requirements, reviewed("Optimicé consultas en PostgreSQL"), SOURCE)!;
    expect(after.after).toBe(80);
    expect(after.requirements.map((item) => item.state)).toEqual(["covered", "missing", "covered"]);
  });

  it("distingue lo que se demuestra con otras palabras y lo que se quitó", () => {
    const requirements = [
      requirement({
        name: "PostgreSQL",
        evidence: [{ kind: "bullet", id: "b1" }],
      }),
      requirement({ name: "Docker", keywords: ["Docker"] }),
      requirement({
        name: "Integración continua",
        keywords: ["CI/CD", "integración continua"],
      }),
    ];

    const match = offerMatch(requirements, reviewed("Optimicé consultas"), SOURCE)!;

    expect(match.requirements.map((item) => item.state)).toEqual([
      // La IA lo da por demostrado, pero no con la palabra de la oferta.
      "unnamed",
      // El perfil tiene Docker, pero la revisión lo dejó fuera.
      "dropped",
      // El logro b2 lo decía y la propuesta no lo eligió.
      "dropped",
    ]);
    expect(match.before).toBe(67);
    expect(match.after).toBe(0);
  });

  it("la formación y los idiomas cuentan como en el CV", () => {
    const requirements = [
      requirement({ name: "Ingeniería", keywords: ["Ingeniería Informática"] }),
      requirement({ name: "Inglés", keywords: ["Inglés B2", "English"] }),
    ];

    expect(offerMatch(requirements, reviewed("x"), SOURCE)!.after).toBe(100);
  });
});

describe("evidenceLabels", () => {
  it("nombra cada evidencia como está en el perfil y omite lo que ya no está", () => {
    const labels = evidenceLabels(
      requirement({
        evidence: [
          { kind: "bullet", id: "b1" },
          { kind: "skill", id: "s-py" },
          { kind: "entry", id: "degree" },
          { kind: "language", id: "l-en" },
          { kind: "skill", id: "borrada" },
        ],
      }),
      SOURCE,
    );

    expect(labels).toEqual([
      "Optimicé consultas en bases de datos relacionales",
      "Python",
      "Ingeniería Informática",
      "Inglés",
    ]);
  });
});
