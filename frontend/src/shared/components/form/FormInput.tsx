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

type FormInputProps<T extends FieldValues> = {
  form: UseFormReturn<T>;
  name: Path<T>;

  label: string;

  type?: React.HTMLInputTypeAttribute;

  /** Solo relevante para type="number", p.ej. "0.01" para permitir decimales. */
  step?: string | number;

  placeholder?: string;

  autoComplete?: string;

  /** Teclado en móvil, p. ej. "numeric" para importes. */
  inputMode?: React.HTMLAttributes<HTMLInputElement>["inputMode"];

  disabled?: boolean;

  startAdornment?: ReactNode;

  endAdornment?: ReactNode;

  className?: string;
};

export function FormInput<T extends FieldValues>({
  form,
  name,
  label,
  type = "text",
  step,
  placeholder,
  autoComplete,
  inputMode,
  disabled,
  startAdornment,
  endAdornment,
  className,
}: FormInputProps<T>) {
  const { t } = useTranslation();

  const {
    field,
    fieldState: { error },
  } = useController({
    control: form.control,
    name,
  });

  return (
    <div className="space-y-2">
      <Label htmlFor={String(name)}>
        {label}
      </Label>

      <div className="relative">
        {startAdornment && (
          <div className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
            {startAdornment}
          </div>
        )}

        <Input
          {...field}
          id={String(name)}
          type={type}
          step={step}
          value={field.value ?? ""}
          placeholder={placeholder}
          autoComplete={autoComplete}
          inputMode={inputMode}
          aria-invalid={!!error}
          disabled={disabled}
          className={[
            startAdornment ? "pl-10" : "",
            endAdornment ? "pr-10" : "",
            className,
          ]
            .filter(Boolean)
            .join(" ")}
        />

        {endAdornment && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            {endAdornment}
          </div>
        )}
      </div>

      {error && (
        <p className="text-sm text-destructive">
          {t(error.message ?? "")}
        </p>
      )}
    </div>
  );
}