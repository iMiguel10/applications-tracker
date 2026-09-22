import { format } from "date-fns";
import { enUS, es } from "date-fns/locale";
import { CalendarIcon } from "lucide-react";
import { useTranslation } from "react-i18next";
import {
  type FieldValues,
  type Path,
  type UseFormReturn,
  useController,
} from "react-hook-form";

import { parseDateOnly, toDateOnly } from "@/shared/lib/dates";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/components/ui/button";
import { Calendar } from "@/shared/components/ui/calendar";
import { Label } from "@/shared/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/shared/components/ui/popover";

const LOCALES = { es, en: enUS } as const;

type FormDatePickerProps<T extends FieldValues> = {
  form: UseFormReturn<T>;
  name: Path<T>;
  label: string;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
};

/**
 * Selector de fecha para campos de tipo `date` de la API: el valor del formulario
 * es un texto "yyyy-MM-dd" (o null), nunca un Date, para no arrastrar zonas horarias.
 */
export function FormDatePicker<T extends FieldValues>({
  form,
  name,
  label,
  placeholder,
  disabled = false,
  className,
}: FormDatePickerProps<T>) {
  const { t, i18n } = useTranslation();
  const locale = LOCALES[i18n.language as keyof typeof LOCALES] ?? enUS;

  const {
    field,
    fieldState: { error },
  } = useController({ control: form.control, name });

  const selected = parseDateOnly(field.value);

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
              className={cn(
                "w-full justify-between text-left font-normal",
                !selected && "text-muted-foreground",
                className,
              )}
            />
          }
        >
          {selected ? format(selected, "P", { locale }) : (placeholder ?? t("common.selectDate"))}
          <CalendarIcon className="h-4 w-4 opacity-50" />
        </PopoverTrigger>

        <PopoverContent className="w-auto p-0" align="start">
          <Calendar
            mode="single"
            selected={selected}
            onSelect={(date) => field.onChange(date ? toDateOnly(date) : null)}
            autoFocus
            locale={locale}
          />
        </PopoverContent>
      </Popover>

      {error && <p className="text-sm text-destructive">{t(error.message ?? "")}</p>}
    </div>
  );
}
