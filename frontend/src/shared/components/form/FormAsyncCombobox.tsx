import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  type FieldValues,
  type Path,
  type UseFormReturn,
  useController,
} from "react-hook-form";

import { useDebounce } from "@/shared/hooks/useDebounce";
import {
  Combobox,
  ComboboxContent,
  ComboboxEmpty,
  ComboboxInput,
  ComboboxItem,
  ComboboxList,
} from "@/shared/components/ui/combobox";
import { Label } from "@/shared/components/ui/label";

export type AsyncComboboxOption = {
  value: string;
  label: string;
};

type Item = AsyncComboboxOption & { create?: true };

type FormAsyncComboboxProps<T extends FieldValues> = {
  form: UseFormReturn<T>;
  name: Path<T>;
  label: string;
  /**
   * Prefijo de la query key de TanStack Query para las opciones. Conviene que cuelgue
   * de la key de la feature (p. ej. [...companyKeys.all, "options"]): así, al invalidar
   * la feature tras crear o editar, el combobox se refresca solo.
   */
  queryKey: readonly unknown[];
  /** Opciones que coinciden con el texto buscado. */
  query: (search: string) => Promise<AsyncComboboxOption[]>;
  /** Para mostrar la etiqueta al editar, cuando el formulario ya trae un id. */
  initialOption?: AsyncComboboxOption | null;
  /**
   * Si se indica, cuando el texto no coincide con ninguna opción aparece "Crear «…»":
   * crea el elemento (p. ej. POST /companies) y lo deja seleccionado (RF-13).
   */
  onCreate?: (label: string) => Promise<AsyncComboboxOption>;
  placeholder?: string;
  emptyMessage?: string;
  disabled?: boolean;
  className?: string;
  debounce?: number;
};

export function FormAsyncCombobox<T extends FieldValues>({
  form,
  name,
  label,
  queryKey,
  query,
  initialOption = null,
  onCreate,
  placeholder,
  emptyMessage,
  disabled = false,
  className,
  debounce = 300,
}: FormAsyncComboboxProps<T>) {
  const { t } = useTranslation();

  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounce(search, debounce);
  // TanStack Query en lugar de fetch en un efecto: estado de carga, descarte de
  // respuestas viejas (si llega tarde la de una búsqueda anterior) y caché.
  const { data: options = [], isFetching: loading } = useQuery({
    queryKey: [...queryKey, debouncedSearch],
    queryFn: () => query(debouncedSearch),
    placeholderData: keepPreviousData,
  });
  const [creating, setCreating] = useState(false);
  // Guardada aparte: la opción elegida puede no estar entre las de la búsqueda actual.
  const [selected, setSelected] = useState<AsyncComboboxOption | null>(initialOption);

  const {
    field,
    fieldState: { error },
  } = useController({ control: form.control, name });

  const typed = search.trim();
  const exactMatch = options.some((o) => o.label.toLowerCase() === typed.toLowerCase());
  const items: Item[] =
    onCreate && typed && !exactMatch && !loading
      ? [...options, { value: `__create__:${typed}`, label: typed, create: true }]
      : options;

  const select = (option: AsyncComboboxOption | null) => {
    setSelected(option);
    field.onChange(option?.value ?? "");
  };

  const handleChange = async (item: Item | null) => {
    if (!item?.create || !onCreate) {
      select(item);
      return;
    }
    setCreating(true);
    try {
      select(await onCreate(item.label));
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-2">
      <Label htmlFor={String(name)}>{label}</Label>

      <Combobox
        items={items}
        value={selected}
        onValueChange={(item) => void handleChange(item as Item | null)}
        onInputValueChange={setSearch}
        itemToStringLabel={(item) => (item as Item | null)?.label ?? ""}
        isItemEqualToValue={(a, b) => (a as Item)?.value === (b as Item)?.value}
        // El filtrado lo hace la API: no volver a filtrar en el cliente.
        filter={null}
        disabled={disabled || creating}
      >
        <ComboboxInput
          id={String(name)}
          placeholder={placeholder}
          onBlur={field.onBlur}
          aria-invalid={!!error}
          className={className}
        />
        <ComboboxContent>
          <ComboboxEmpty>
            {loading ? t("common.loading") : (emptyMessage ?? t("common.noResults"))}
          </ComboboxEmpty>
          <ComboboxList>
            {(item: Item) => (
              <ComboboxItem key={item.value} value={item}>
                {item.create ? t("common.createOption", { label: item.label }) : item.label}
              </ComboboxItem>
            )}
          </ComboboxList>
        </ComboboxContent>
      </Combobox>

      {error && <p className="text-sm text-destructive">{t(error.message ?? "")}</p>}
    </div>
  );
}
