import { useEffect } from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { useForm, type UseFormReturn } from "react-hook-form";
import { afterEach, beforeAll, describe, expect, it } from "vitest";

import i18n from "@/shared/i18n/i18n";
import { FormDatePicker } from "./FormDatePicker";
import { FormDateTimePicker } from "./FormDateTimePicker";
import { FormInput } from "./FormInput";
import { FormSelect } from "./FormSelect";
import { FormTextarea } from "./FormTextarea";

type Values = { field: string | null };
type FieldRenderer = (form: UseFormReturn<Values>) => React.ReactNode;

const LABEL = "Campo";
const ERROR_KEY = "companies.validation.nameRequired";

const fields: [string, FieldRenderer][] = [
  ["FormInput", (form) => <FormInput form={form} name="field" label={LABEL} />],
  ["FormTextarea", (form) => <FormTextarea form={form} name="field" label={LABEL} />],
  [
    "FormSelect",
    (form) => (
      <FormSelect form={form} name="field" label={LABEL} options={[{ value: "a", label: "A" }]} />
    ),
  ],
  ["FormDatePicker", (form) => <FormDatePicker form={form} name="field" label={LABEL} />],
  ["FormDateTimePicker", (form) => <FormDateTimePicker form={form} name="field" label={LABEL} />],
];

function Harness({ renderField, withError }: { renderField: FieldRenderer; withError: boolean }) {
  const form = useForm<Values>({ defaultValues: { field: null } });
  useEffect(() => {
    if (withError) form.setError("field", { message: ERROR_KEY });
  }, [form, withError]);
  return <>{renderField(form)}</>;
}

describe.each(fields)("%s accessibility", (_name, renderField) => {
  afterEach(cleanup);

  beforeAll(async () => {
    await i18n.changeLanguage("es");
  });

  it("is reachable through its label and has no aria-describedby while valid", () => {
    render(<Harness renderField={renderField} withError={false} />);

    const control = screen.getByLabelText(LABEL);
    expect(control).not.toHaveAttribute("aria-describedby");
    expect(control).not.toHaveAttribute("aria-invalid", "true");
  });

  it("points aria-describedby at the rendered error message when invalid", async () => {
    render(<Harness renderField={renderField} withError />);

    const message = await screen.findByText(i18n.t(ERROR_KEY));
    const control = screen.getByLabelText(LABEL);
    const describedBy = control.getAttribute("aria-describedby");
    expect(describedBy).toBeTruthy();
    expect(document.getElementById(describedBy!)).toBe(message);
    expect(control).toHaveAttribute("aria-invalid", "true");
    expect(control).toHaveAccessibleDescription(i18n.t(ERROR_KEY));
  });
});
