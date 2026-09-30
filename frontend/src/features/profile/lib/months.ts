/** Mes y año del perfil. La API guarda fechas (`yyyy-MM-dd`, día 1) y el formulario
 * los elige por separado: `<input type="month">` sale como texto libre en
 * Firefox y Safari de escritorio. */

export type MonthYear = { month: string | null; year: string | null };

export function toMonthYear(date: string | null): MonthYear {
  if (!date) return { month: null, year: null };
  const [year, month] = date.split("-");
  return { month, year };
}

/** `null` salvo que estén los dos: la validación del formulario ya exige ambos. */
export function fromMonthYear({ month, year }: MonthYear): string | null {
  return month && year ? `${year}-${month}-01` : null;
}

/** Los doce meses con su nombre en el idioma de la interfaz. */
export function monthOptions(locale: string): { value: string; label: string }[] {
  const format = new Intl.DateTimeFormat(locale, { month: "long", timeZone: "UTC" });
  return Array.from({ length: 12 }, (_, index) => {
    const label = format.format(new Date(Date.UTC(2000, index, 1)));
    return {
      value: String(index + 1).padStart(2, "0"),
      label: label.charAt(0).toLocaleUpperCase(locale) + label.slice(1),
    };
  });
}

/** Años de más reciente a más antiguo: hasta 5 por delante (una formación que
 * termina en el futuro) y hasta 1950. */
export function yearOptions(now: Date = new Date()): { value: string; label: string }[] {
  const last = now.getFullYear() + 5;
  return Array.from({ length: last - 1950 + 1 }, (_, index) => {
    const year = String(last - index);
    return { value: year, label: year };
  });
}

/** "mar 2021", en el idioma de la interfaz. */
export function formatMonth(date: string, locale: string): string {
  const { month, year } = toMonthYear(date);
  return new Intl.DateTimeFormat(locale, {
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(Date.UTC(Number(year), Number(month) - 1, 1)));
}
