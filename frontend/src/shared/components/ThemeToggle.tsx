import { Moon, Sun } from "lucide-react";
import { useTranslation } from "react-i18next";

import { useTheme } from "@/app/providers/useTheme";
import { cn } from "@/shared/lib/utils";
import { Switch } from "@/shared/components/ui/switch";

/** Interruptor claro/oscuro (F8.4): la misma pieza para la navegación y las
 * preferencias, ambas comparten el `ThemeProvider`. */
export function ThemeToggle({ className }: { className?: string }) {
  const { t } = useTranslation();
  const { resolvedTheme, setTheme } = useTheme();
  const isDark = resolvedTheme === "dark";

  return (
    <label className={cn("inline-flex cursor-pointer items-center gap-2", className)}>
      <span className="sr-only">{t("nav.theme")}</span>
      <Sun className="size-4 text-muted-foreground" aria-hidden />
      <Switch
        checked={isDark}
        onCheckedChange={(checked) => setTheme(checked ? "dark" : "light")}
      />
      <Moon className="size-4 text-muted-foreground" aria-hidden />
    </label>
  );
}
