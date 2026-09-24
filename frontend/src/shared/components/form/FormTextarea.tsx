import { useTranslation } from "react-i18next";
import {
  type FieldValues,
  type Path,
  type UseFormReturn,
  useController,
} from "react-hook-form";

import { Label } from "@/shared/components/ui/label";
import { Textarea } from "@/shared/components/ui/textarea";

type Props<T extends FieldValues> = {
  form: UseFormReturn<T>;
  name: Path<T>;

  label: string;

  placeholder?: string;

  rows?: number;

  disabled?: boolean;
};

export function FormTextarea<T extends FieldValues>({
  form,
  name,
  label,
  placeholder,
  rows = 4,
  disabled,
}: Props<T>) {
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

      <Textarea
        {...field}
        id={String(name)}
        rows={rows}
        placeholder={placeholder}
        disabled={disabled}
        aria-invalid={!!error}
        aria-describedby={error ? `${String(name)}-error` : undefined}
      />

      {error && (
        <p id={`${String(name)}-error`} className="text-sm text-destructive">
          {t(error.message ?? "")}
        </p>
      )}

    </div>
  );
}