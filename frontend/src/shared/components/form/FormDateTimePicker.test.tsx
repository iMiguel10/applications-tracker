import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { useForm } from "react-hook-form";
import { afterEach, beforeAll, describe, expect, it } from "vitest";

import { authKeys } from "@/features/auth/auth.keys";
import i18n from "@/shared/i18n/i18n";
import { browserZone } from "@/shared/lib/dates";
import { FormDateTimePicker } from "./FormDateTimePicker";

function Harness() {
  const form = useForm<{ when: string }>({ defaultValues: { when: "2026-10-07T09:30" } });
  return <FormDateTimePicker form={form} name="when" label="Cuándo" />;
}

function renderWithZone(timezone: string | null) {
  const queryClient = new QueryClient();
  queryClient.setQueryData(authKeys.preferences(), { timezone });
  render(
    <QueryClientProvider client={queryClient}>
      <Harness />
    </QueryClientProvider>,
  );
}

// Una zona que nunca será la del entorno de pruebas.
const OTHER_ZONE = browserZone() === "Pacific/Kiritimati" ? "Pacific/Pago_Pago" : "Pacific/Kiritimati";

beforeAll(async () => {
  await i18n.changeLanguage("es");
});

afterEach(cleanup);

describe("FormDateTimePicker", () => {
  it("dice en qué zona se escribe la hora si la de la cuenta no es la del navegador", () => {
    renderWithZone(OTHER_ZONE);

    expect(screen.getByText(i18n.t("common.timesIn", { zone: OTHER_ZONE }))).toBeInTheDocument();
  });

  it("no dice nada si la cuenta usa la zona del navegador o no tiene", () => {
    renderWithZone(browserZone());
    renderWithZone(null);

    expect(screen.queryByText(/^Horas en /)).not.toBeInTheDocument();
  });
});
