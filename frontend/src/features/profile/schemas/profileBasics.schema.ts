import { z } from "zod";

import { MAX_LINKS, SUMMARY_MAX_LENGTH, type Profile } from "../types/Profile";

// Solo formato, para dar respuesta inmediata. La autoridad es el backend.
const optionalText = (max: number) =>
  z.string().trim().max(max, "common.validation.tooLong");

const linkSchema = z.object({
  label: z
    .string()
    .trim()
    .min(1, "profile.validation.linkLabelRequired")
    .max(50, "common.validation.tooLong"),
  // Solo http(s): los enlaces se pintan como <a href> aquí y en el PDF.
  url: z
    .string()
    .trim()
    .max(500, "common.validation.tooLong")
    .refine((v) => /^https?:\/\/[^\s/]+\S*$/i.test(v), "common.validation.url"),
});

export const profileBasicsSchema = z.object({
  full_name: optionalText(200),
  headline: optionalText(200),
  contact_email: z
    .string()
    .trim()
    .max(254, "common.validation.tooLong")
    .refine((v) => v === "" || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v), "profile.validation.email"),
  phone: z
    .string()
    .trim()
    .max(50, "common.validation.tooLong")
    .refine((v) => v === "" || /^[0-9+()./\- ]+$/.test(v), "profile.validation.phone"),
  location: optionalText(200),
  links: z.array(linkSchema).max(MAX_LINKS),
  summary: z.string().trim().max(SUMMARY_MAX_LENGTH, "profile.validation.summaryTooLong"),
});

export type ProfileBasicsFormValues = z.infer<typeof profileBasicsSchema>;

/** Los valores del formulario a partir del perfil guardado. Si nunca se ha guardado
 * un email de contacto, propone el de la cuenta. */
export function toProfileBasicsForm(
  profile: Profile,
  accountEmail?: string | null,
): ProfileBasicsFormValues {
  return {
    full_name: profile.full_name ?? "",
    headline: profile.headline ?? "",
    contact_email: profile.contact_email ?? accountEmail ?? "",
    phone: profile.phone ?? "",
    location: profile.location ?? "",
    links: profile.links,
    summary: profile.summary ?? "",
  };
}
