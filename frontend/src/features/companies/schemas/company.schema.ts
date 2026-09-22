import { z } from "zod";

// Solo formato, para dar respuesta inmediata. La autoridad es el backend (unicidad
// del nombre incluida: llega como 409 company_name_taken).
export const companySchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "companies.validation.nameRequired")
    .max(200, "common.validation.tooLong"),
  website: z
    .string()
    .trim()
    .max(500, "common.validation.tooLong")
    .refine((v) => v === "" || /^https?:\/\/\S+$/.test(v), "common.validation.url"),
  location: z.string().trim().max(200, "common.validation.tooLong"),
  notes: z.string().max(5000, "common.validation.notesTooLong"),
});

export type CompanyFormValues = z.infer<typeof companySchema>;

export const emptyCompanyForm: CompanyFormValues = {
  name: "",
  website: "",
  location: "",
  notes: "",
};
