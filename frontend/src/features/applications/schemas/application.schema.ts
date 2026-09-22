import { z } from "zod";
import { APPLICATION_SOURCES, INITIAL_STATUSES, WORK_MODES } from "../types/Application";

const salary = z
  .string()
  .trim()
  .refine((v) => v === "" || /^\d{1,9}$/.test(v), "applications.validation.salaryNumber");

// Solo formato, para dar respuesta inmediata. La autoridad es el backend, que valida
// además las reglas que dependen de lo ya guardado (p. ej. el salario en un PATCH).
export const applicationSchema = z
  .object({
    company_id: z.string().min(1, "applications.validation.companyRequired"),
    position_title: z
      .string()
      .trim()
      .min(1, "applications.validation.positionRequired")
      .max(200, "common.validation.tooLong"),
    job_url: z
      .string()
      .trim()
      .max(2000, "common.validation.tooLong")
      .refine((v) => v === "" || /^https?:\/\/\S+$/.test(v), "common.validation.url"),
    location: z.string().trim().max(200, "common.validation.tooLong"),
    work_mode: z.enum(WORK_MODES).nullable(),
    source: z.enum(APPLICATION_SOURCES).nullable(),
    // Solo se usa al crear: el estado no se edita con el formulario (invariante 3).
    status: z.enum(INITIAL_STATUSES),
    applied_at: z.string().nullable(),
    salary_min: salary,
    salary_max: salary,
    salary_currency: z
      .string()
      .trim()
      .regex(/^[A-Za-z]{3}$/, "applications.validation.currency"),
    notes: z.string().max(5000, "common.validation.notesTooLong"),
  })
  .refine(
    (v) => v.salary_min === "" || v.salary_max === "" || Number(v.salary_min) <= Number(v.salary_max),
    { message: "errors.salary_range_invalid", path: ["salary_max"] },
  );

export type ApplicationFormValues = z.infer<typeof applicationSchema>;
