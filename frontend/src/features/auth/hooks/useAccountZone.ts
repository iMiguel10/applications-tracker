import { accountZone } from "@/shared/lib/dates";
import { usePreferences } from "./queries/usePreferences";

/**
 * La zona horaria en la que la interfaz muestra y pide las horas: la de la cuenta
 * (RF-07), la misma de los emails y del calendario, o la del navegador si la cuenta
 * no tiene (o mientras se cargan las preferencias).
 */
export function useAccountZone(): string {
  const { data } = usePreferences();
  return accountZone(data?.timezone);
}
