import { createContext } from "react";

export type Theme = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

export interface ThemeContextValue {
  theme: Theme;
  resolvedTheme: ResolvedTheme;
  setTheme: (theme: Theme) => void;
  /** Suma/resta una petición de "forzar claro" (login/registro, ver `useForceLightTheme`). */
  setForceLight: (active: boolean) => void;
}

export const ThemeContext = createContext<ThemeContextValue | null>(null);
