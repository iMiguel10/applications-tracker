import { toDateOnly } from "@/shared/lib/dates";
import type { ApplicationFormValues } from "../schemas/application.schema";
import type { ApplicationDetail } from "../types/Application";

/** Formulario vacío para crear: enviada hoy, en euros. */
export function emptyApplicationForm(companyId = ""): ApplicationFormValues {
  return {
    company_id: companyId,
    position_title: "",
    job_url: "",
    location: "",
    work_mode: null,
    source: null,
    status: "applied",
    applied_at: toDateOnly(new Date()),
    salary_min: "",
    salary_max: "",
    salary_currency: "EUR",
    notes: "",
    job_description: "",
    cv_document_id: null,
    cover_letter_document_id: null,
  };
}

export function toFormValues(application: ApplicationDetail): ApplicationFormValues {
  const text = (value: number | null) => (value === null ? "" : String(value));
  return {
    company_id: application.company.id,
    position_title: application.position_title,
    job_url: application.job_url ?? "",
    location: application.location ?? "",
    work_mode: application.work_mode,
    source: application.source,
    // Solo se usa al crear; al editar el estado no se toca (invariante 3).
    status: application.status === "saved" ? "saved" : "applied",
    applied_at: application.applied_at,
    salary_min: text(application.salary_min),
    salary_max: text(application.salary_max),
    salary_currency: application.salary_currency,
    notes: application.notes ?? "",
    job_description: application.job_description ?? "",
    cv_document_id: application.cv_document?.id ?? null,
    cover_letter_document_id: application.cover_letter_document?.id ?? null,
  };
}
