import { type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import {
  type FieldValues,
  type Path,
  type UseFormReturn,
  useController,
} from "react-hook-form";

import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";

type FormFileInputProps<T extends FieldValues> = {
  form: UseFormReturn<T>;
  name: Path<T>;
  label: string;
  /** Tipos que ofrece el selector del sistema, p. ej. "application/pdf,.pdf". */
  accept?: string;
  /** Texto de ayuda bajo el campo (p. ej. el tamaño máximo). */
  hint?: ReactNode;
  disabled?: boolean;
};

/**
 * Un fichero como valor del formulario (`File | null`). Un `<input type="file">`
 * no admite `value` controlado: el campo solo escucha `onChange`.
 */
export function FormFileInput<T extends FieldValues>({
  form,
  name,
  label,
  accept,
  hint,
  disabled,
}: FormFileInputProps<T>) {
  const { t } = useTranslation();
  const {
    field,
    fieldState: { error },
  } = useController({ control: form.control, name });

  const id = String(name);
  const describedBy = [error && `${id}-error`, hint && `${id}-hint`].filter(Boolean).join(" ");

  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <Input
        {...field}
        // Sin `value`: un input de fichero no se puede controlar.
        value={undefined}
        id={id}
        type="file"
        accept={accept}
        disabled={disabled}
        onChange={(event) => field.onChange(event.target.files?.[0] ?? null)}
        aria-invalid={!!error}
        aria-describedby={describedBy || undefined}
        className="cursor-pointer file:cursor-pointer"
      />
      {hint && (
        <p id={`${id}-hint`} className="text-sm text-muted-foreground">
          {hint}
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
