import { z } from "zod";

import { fromMonthYear, toMonthYear } from "../lib/months";
import {
  ENTRY_DESCRIPTION_MAX_LENGTH,
  MAX_BULLETS_PER_ENTRY,
  type EntryInput,
  type ProfileEntry,
} from "../types/ProfileEntry";

const optionalText = (max: number) => z.string().trim().max(max, "common.validation.tooLong");

// Solo formato, para dar respuesta inmediata. La autoridad es el backend.
export const entrySchema = z
  .object({
    title: z
      .string()
      .trim()
      .min(1, "profile.validation.titleRequired")
      .max(200, "common.validation.tooLong"),
    organization: optionalText(200),
    location: optionalText(200),
    start_month: z.string().nullable(),
    start_year: z.string().nullable(),
    end_month: z.string().nullable(),
    end_year: z.string().nullable(),
    is_current: z.boolean(),
    description: z
      .string()
      .trim()
      .max(ENTRY_DESCRIPTION_MAX_LENGTH, "profile.validation.summaryTooLong"),
    bullets: z
      .array(
        z.object({
          // El del logro guardado; sin él, es nuevo. La clave de la fila en la lista
          // es otra (`keyName: "key"` en `useFieldArray`).
          id: z.string().optional(),
          text: z
            .string()
            .trim()
            .min(1, "profile.validation.bulletRequired")
            .max(500, "common.validation.tooLong"),
        }),
      )
      .max(MAX_BULLETS_PER_ENTRY),
  })
  .superRefine((values, ctx) => {
    // Mes y año van juntos: uno sin el otro no es una fecha.
    for (const side of ["start", "end"] as const) {
      const month = values[`${side}_month`];
      const year = values[`${side}_year`];
      if (!!month !== !!year) {
        ctx.addIssue({
          code: "custom",
          path: [month ? `${side}_year` : `${side}_month`],
          message: "profile.validation.monthAndYear",
        });
      }
    }
    const start = fromMonthYear({ month: values.start_month, year: values.start_year });
    const end = fromMonthYear({ month: values.end_month, year: values.end_year });
    if (!values.is_current && start && end && end < start) {
      ctx.addIssue({
        code: "custom",
        path: ["end_year"],
        message: "profile.validation.endBeforeStart",
      });
    }
  });

export type EntryFormValues = z.infer<typeof entrySchema>;

export function toEntryForm(entry: ProfileEntry | null): EntryFormValues {
  const start = toMonthYear(entry?.start_date ?? null);
  const end = toMonthYear(entry?.end_date ?? null);
  return {
    title: entry?.title ?? "",
    organization: entry?.organization ?? "",
    location: entry?.location ?? "",
    start_month: start.month,
    start_year: start.year,
    end_month: end.month,
    end_year: end.year,
    is_current: entry?.is_current ?? false,
    description: entry?.description ?? "",
    bullets: (entry?.bullets ?? []).map((bullet) => ({
      id: bullet.id,
      text: bullet.text,
    })),
  };
}

export function toEntryInput(values: EntryFormValues): EntryInput {
  return {
    title: values.title,
    organization: values.organization,
    location: values.location,
    start_date: fromMonthYear({ month: values.start_month, year: values.start_year }),
    // "Actualidad" no tiene fecha de fin, aunque quedara elegida de antes.
    end_date: values.is_current
      ? null
      : fromMonthYear({ month: values.end_month, year: values.end_year }),
    is_current: values.is_current,
    description: values.description,
    bullets: values.bullets.map(({ id, text }) => (id ? { id, text } : { text })),
  };
}
