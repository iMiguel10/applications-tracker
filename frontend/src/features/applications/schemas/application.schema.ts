import { z } from "zod";

// Solo validación de formato para dar respuesta inmediata en el formulario.
// La autoridad es el backend (ApplicationCreate), que vuelve a validar.
export const createApplicationSchema = z.object({
  position_title: z
    .string()
    .trim()
    .min(1, "applications.validation.positionRequired")
    .max(200, "applications.validation.tooLong"),
  company_name: z
    .string()
    .trim()
    .min(1, "applications.validation.companyRequired")
    .max(200, "applications.validation.tooLong"),
});

export type CreateApplicationFormValues = z.infer<typeof createApplicationSchema>;
