import {
  useCallback,
  useLayoutEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { ThemeContext, type Theme, type ResolvedTheme } from "./theme-context";

const STORAGE_KEY = "theme";

function systemPrefersDark() {
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function readStoredTheme(): Theme {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored === "light" || stored === "dark" ? stored : "system";
}

function resolveTheme(theme: Theme): ResolvedTheme {
  return theme === "system" ? (systemPrefersDark() ? "dark" : "light") : theme;
}

/** Tema claro/oscuro (F8.4): solo en el navegador, vía localStorage — no es una
 * preferencia de cuenta como el idioma, así que no pasa por el backend. `index.html`
 * aplica el valor guardado antes de este componente para evitar un parpadeo al claro.
 *
 * Login y registro (`AuthLayout`, vía `useForceLightTheme`) ignoran el tema: su panel
 * de marca es oscuro siempre y el lado del formulario está pensado para leerse junto a
 * él, así que en modo oscuro los dos paneles casi se funden y el contraste que da
 * sentido al diseño desaparece. `forceLightCount` (con recuento, no un booleano, por si
 * algún día hay más de un componente pidiéndolo a la vez) prevalece sobre el tema
 * elegido, pero no lo cambia: `resolvedTheme` sigue siendo el real para el interruptor
 * de navegación y preferencias, solo la clase `dark` que de verdad pinta la página se
 * calcula a partir de `appliedTheme`. Todo pasa por este único efecto para que no haya
 * dos sitios escribiendo esa clase a la vez. */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(readStoredTheme);
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>(() => resolveTheme(theme));
  const [forceLightCount, setForceLightCount] = useState(0);

  const appliedTheme: ResolvedTheme = forceLightCount > 0 ? "light" : resolvedTheme;

  useLayoutEffect(() => {
    document.documentElement.classList.toggle("dark", appliedTheme === "dark");
  }, [appliedTheme]);

  useLayoutEffect(() => {
    if (theme !== "system") return;
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => setResolvedTheme(systemPrefersDark() ? "dark" : "light");
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, [theme]);

  const setTheme = useCallback((next: Theme) => {
    setThemeState(next);
    setResolvedTheme(resolveTheme(next));
    if (next === "system") {
      localStorage.removeItem(STORAGE_KEY);
    } else {
      localStorage.setItem(STORAGE_KEY, next);
    }
  }, []);

  const setForceLight = useCallback((active: boolean) => {
    setForceLightCount((count) => count + (active ? 1 : -1));
  }, []);

  const value = useMemo(
    () => ({ theme, resolvedTheme, setTheme, setForceLight }),
    [theme, resolvedTheme, setTheme, setForceLight],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}
