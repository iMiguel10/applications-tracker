import { useTranslation } from "react-i18next";
import {
  type FieldValues,
  type Path,
  type UseFormReturn,
  useController,
} from "react-hook-form";

import {
  Combobox,
  ComboboxContent,
  ComboboxEmpty,
  ComboboxInput,
  ComboboxItem,
  ComboboxList,
} from "@/shared/components/ui/combobox";
import { Label } from "@/shared/components/ui/label";
import type { SelectOption } from "./FormSelect";

type FormComboboxProps<T extends FieldValues> = {
  form: UseFormReturn<T>;
  name: Path<T>;
  label: string;
  /** Todas las opciones: se filtran en el cliente al escribir. Para listas que
   * vienen de la API y se buscan allí, `FormAsyncCombobox`. */
  options: readonly SelectOption[];
  placeholder?: string;
  description?: string;
  disabled?: boolean;
  className?: string;
};

/** Selector con buscador para listas largas y fijas (p. ej. zonas horarias). El
 * valor del formulario es el `value` de la opción, o null si se vacía. */
export function FormCombobox<T extends FieldValues>({
  form,
  name,
  label,
  options,
  placeholder,
  description,
  disabled = false,
  className,
}: FormComboboxProps<T>) {
  const { t } = useTranslation();
  const {
    field,
    fieldState: { error },
  } = useController({ control: form.control, name });

  const selected = options.find((option) => option.value === field.value) ?? null;
  const id = String(name);
  const describedBy =
    [error ? `${id}-error` : null, description ? `${id}-description` : null]
      .filter(Boolean)
      .join(" ") || undefined;

  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>

      <Combobox
        items={options}
        value={selected}
        onValueChange={(item) => field.onChange((item as SelectOption | null)?.value ?? null)}
        itemToStringLabel={(item) => (item as SelectOption | null)?.label ?? ""}
        isItemEqualToValue={(a, b) => (a as SelectOption)?.value === (b as SelectOption)?.value}
        disabled={disabled}
      >
        <ComboboxInput
          id={id}
          placeholder={placeholder}
          onBlur={field.onBlur}
          aria-invalid={!!error}
          aria-describedby={describedBy}
          className={className}
          triggerLabel={t("common.showOptions")}
          clearLabel={t("common.clearSelection")}
        />
        <ComboboxContent>
          <ComboboxEmpty>{t("common.noResults")}</ComboboxEmpty>
          <ComboboxList>
            {(item: SelectOption) => (
              <ComboboxItem key={item.value} value={item}>
                {item.label}
              </ComboboxItem>
            )}
          </ComboboxList>
        </ComboboxContent>
      </Combobox>

      {description && (
        <p id={`${id}-description`} className="text-sm text-muted-foreground">
          {description}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className="text-sm text-destructive">
          {t(error.message ?? "")}
        </p>
      )}
    </div>
  );
}
