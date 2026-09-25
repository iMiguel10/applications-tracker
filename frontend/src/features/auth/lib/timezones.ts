import type { SelectOption } from "@/shared/components/form";

/** Zona IANA del navegador ("Europe/Madrid"), o null si no la expone. */
export function browserTimezone(): string | null {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || null;
  } catch {
    return null;
  }
}

function currentOffset(timezone: string, locale: string): string {
  try {
    const parts = new Intl.DateTimeFormat(locale, {
      timeZone: timezone,
      timeZoneName: "shortOffset",
    }).formatToParts(new Date());
    return parts.find((part) => part.type === "timeZoneName")?.value ?? "";
  } catch {
    return "";
  }
}

/**
 * Zonas que conoce el navegador, más UTC y la guardada (por si el navegador no la
 * tiene en su lista). La etiqueta lleva el desfase de HOY, que cambia con el
 * horario de verano: es orientativo, lo que se guarda es el nombre (A39).
 */
export function timezoneOptions(locale: string, current: string | null): SelectOption[] {
  const zones = new Set(Intl.supportedValuesOf("timeZone"));
  zones.add("UTC");
  if (current) zones.add(current);
  return [...zones].sort().map((zone) => {
    const offset = currentOffset(zone, locale);
    const name = zone.replaceAll("_", " ");
    return { value: zone, label: offset ? `${name} (${offset})` : name };
  });
}
