import { describe, expect, it } from "vitest";

import type { ApplicationDetail } from "../types/Application";
import { emptyApplicationForm, toFormValues } from "./formValues";

const application: ApplicationDetail = {
  id: "a1",
  company: { id: "c1", name: "Acme" },
  position_title: "Backend",
  job_url: null,
  location: null,
  work_mode: null,
  source: null,
  origin: "manual",
  status: "applied",
  allowed_transitions: [],
  applied_at: "2026-09-30",
  salary_min: null,
  salary_max: null,
  salary_currency: "EUR",
  notes: null,
  archived_at: null,
  last_activity_at: "2026-09-30T10:00:00Z",
  created_at: "2026-09-30T10:00:00Z",
  updated_at: "2026-09-30T10:00:00Z",
  job_description: null,
  cv_document: {
    id: "d1",
    kind: "cv",
    name: "cv.pdf",
    status: "ready",
    archived_at: "2026-09-30T11:00:00Z",
  },
  cover_letter_document: null,
};

describe("formValues de la solicitud (RF-27, RF-28)", () => {
  it("nace sin descripción ni documentos", () => {
    const values = emptyApplicationForm();
    expect(values.job_description).toBe("");
    expect(values.cv_document_id).toBeNull();
    expect(values.cover_letter_document_id).toBeNull();
  });

  it("toma los ids de los documentos enviados, también si están archivados", () => {
    const values = toFormValues(application);
    expect(values.cv_document_id).toBe("d1");
    expect(values.cover_letter_document_id).toBeNull();
    expect(values.job_description).toBe("");
  });
});
