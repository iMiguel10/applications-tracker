import { useId } from "react";
import { format, isValid, parse } from "date-fns";
import { enUS, es } from "date-fns/locale";
import { CalendarClock, Clock } from "lucide-react";
import { useTranslation } from "react-i18next";
import {
  type FieldValues,
  type Path,
  type UseFormReturn,
  useController,
} from "react-hook-form";

import { toDateOnly } from "@/shared/lib/dates";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/components/ui/button";
import { Calendar } from "@/shared/components/ui/calendar";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/shared/components/ui/popover";

const LOCALES = { es, en: enUS } as const;
const VALUE_FORMAT = "yyyy-MM-dd'T'HH:mm";
// Hora que se propone al elegir primero el día: una hora de oficina, no medianoche.
const DEFAULT_TIME = "09:00";

type FormDateTimePickerProps<T extends FieldValues> = {
  form: UseFormReturn<T>;
  name: Path<T>;
  label: string;
  placeholder?: string;
  disabled?: boolean;
};

/**
 * Fecha y hora con el mismo calendario que `FormDatePicker`, en vez del
 * `datetime-local` nativo (que pinta el navegador y no sigue la paleta ni el tema).
 * El valor es el mismo texto que daba ese input, "yyyy-MM-ddTHH:mm" en hora LOCAL,
 * así que `datetimeLocalToIso`/`toDateTimeLocal` siguen sirviendo tal cual.
 */
export function FormDateTimePicker<T extends FieldValues>({
  form,
  name,
  label,
  placeholder,
  disabled = false,
}: FormDateTimePickerProps<T>) {
  const { t, i18n } = useTranslation();
  const locale = LOCALES[i18n.language as keyof typeof LOCALES] ?? enUS;
  const timeId = useId();

  const {
    field,
    fieldState: { error },
  } = useController({ control: form.control, name });

  const parsed = field.value ? parse(field.value, VALUE_FORMAT, new Date()) : undefined;
  const selected = parsed && isValid(parsed) ? parsed : undefined;
  const time = selected ? format(selected, "HH:mm") : "";

  const setDate = (date: Date | undefined) => {
    if (!date) return;
    field.onChange(`${toDateOnly(date)}T${time || DEFAULT_TIME}`);
  };

  const setTime = (value: string) => {
    if (!value) return;
    field.onChange(`${toDateOnly(selected ?? new Date())}T${value}`);
  };

  return (
    <div className="space-y-2">
      <Label htmlFor={String(name)}>{label}</Label>

      <Popover>
        <PopoverTrigger
          render={
            <Button
              id={String(name)}
              type="button"
              variant="outline"
              disabled={disabled}
              aria-invalid={!!error}
              aria-describedby={error ? `${String(name)}-error` : undefined}
              className={cn(
                "w-full justify-between text-left font-normal",
                !selected && "text-muted-foreground",
              )}
            />
          }
        >
          {selected
            ? format(selected, "PPPp", { locale })
            : (placeholder ?? t("common.selectDateTime"))}
          <CalendarClock className="h-4 w-4 opacity-50" />
        </PopoverTrigger>

        <PopoverContent className="w-auto p-0" align="start">
          <Calendar
            mode="single"
            selected={selected}
            onSelect={setDate}
            autoFocus
            locale={locale}
          />
          <div className="flex items-center gap-3 border-t px-3 py-2.5">
            <Clock className="size-4 text-muted-foreground" aria-hidden />
            <Label htmlFor={timeId} className="font-normal text-muted-foreground">
              {t("common.time")}
            </Label>
            <Input
              id={timeId}
              type="time"
              step={300}
              value={time}
              onChange={(event) => setTime(event.target.value)}
              // El reloj nativo abriría otro selector del navegador encima de este.
              className="ml-auto h-8 w-28 [&::-webkit-calendar-picker-indicator]:hidden"
            />
          </div>
        </PopoverContent>
      </Popover>

      {error && (
        <p id={`${String(name)}-error`} className="text-sm text-destructive">
          {t(error.message ?? "")}
        </p>
      )}
    </div>
  );
}
