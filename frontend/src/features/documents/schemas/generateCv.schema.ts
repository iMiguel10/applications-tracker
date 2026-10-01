import { z } from "zod";

/** El diseño, el idioma y el nombre del CV que se genera (RF-103). Las secciones y
 * los elementos van aparte (`lib/cvSelection.ts`): son casillas, no campos. */
export const generateCvSchema = z.object({
  name: z.string().trim().min(1, "documents.validation.nameRequired").max(200),
  design: z.string().min(1, "documents.generate.designRequired"),
  language: z.string().min(1),
});

export type GenerateCvFormValues = z.infer<typeof generateCvSchema>;
