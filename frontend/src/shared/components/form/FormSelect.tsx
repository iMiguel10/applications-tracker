import { useTranslation } from "react-i18next";
import {
  type FieldValues,
  type Path,
  type UseFormReturn,
  useController,
} from "react-hook-form";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import { Label } from "@/shared/components/ui/label";

export type SelectOption = { value: string; label: string };

const EMPTY = "__empty__";

type FormSelectProps<T extends FieldValues> = {
  form: UseFormReturn<T>;
  name: Path<T>;
  label: string;
  options: readonly SelectOption[];
  /**
   * Para campos opcionales: añade una primera opción con esta etiqueta que deja el
   * campo en null (lo que espera la API), no en "".
   */
  emptyLabel?: string;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
};

export function FormSelect<T extends FieldValues>({
  form,
  name,
  label,
  options,
  emptyLabel,
  placeholder,
  disabled,
  className,
}: FormSelectProps<T>) {
  const { t } = useTranslation();
  const {
    field,
    fieldState: { error },
  } = useController({ control: form.control, name });

  const items = emptyLabel ? [{ value: EMPTY, label: emptyLabel }, ...options] : options;
  const value = field.value ?? (emptyLabel ? EMPTY : "");

  return (
    <div className="space-y-2">
      <Label htmlFor={String(name)}>{label}</Label>

      <Select
        items={items}
        value={value}
        onValueChange={(next) => field.onChange(next === EMPTY ? null : next)}
        disabled={disabled}
      >
        <SelectTrigger
          id={String(name)}
          className={className ?? "w-full"}
          onBlur={field.onBlur}
          aria-invalid={!!error}
          aria-describedby={error ? `${String(name)}-error` : undefined}
        >
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent>
          {items.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {error && <p id={`${String(name)}-error`} className="text-sm text-destructive">{t(error.message ?? "")}</p>}
    </div>
  );
}
