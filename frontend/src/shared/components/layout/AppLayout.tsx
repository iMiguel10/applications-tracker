import { Menu, Settings } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { NavLink, Outlet } from "react-router-dom";

import i18n from "@/shared/i18n/i18n";
import { cn } from "@/shared/lib/utils";
import { Button, buttonVariants } from "@/shared/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/shared/components/ui/popover";
import { ThemeToggle } from "@/shared/components/ThemeToggle";
import { NAV_ITEMS } from "@/shared/config/navigation";
import { LANGUAGES, type Language } from "@/features/auth/types/Auth";
import { useMe } from "@/features/auth/hooks/queries/useMe";
import { usePreferences } from "@/features/auth/hooks/queries/usePreferences";
import { useSignOut } from "@/features/auth/hooks/mutations/useSignOut";

const I18NEXT_LNG_STORAGE_KEY = "i18nextLng";

function detectBrowserLanguage(): Language {
  const short = navigator.language.split("-")[0];
  return (LANGUAGES as readonly string[]).includes(short) ? (short as Language) : "es";
}

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  cn(
    "flex items-center gap-2 rounded-md px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted hover:text-foreground",
    isActive && "bg-muted font-medium text-foreground",
  );

/** Marco de las páginas autenticadas: navegación, usuario y cierre de sesión. */
export function AppLayout() {
  const { t } = useTranslation();
  const { data: me } = useMe();
  const { data: preferences } = usePreferences();
  const signOut = useSignOut();
  const [menuOpen, setMenuOpen] = useState(false);

  // Preferencia guardada (F8): "null" significa seguir el navegador, así que se
  // limpia la caché de i18next para que vuelva a detectarlo, no que se quede en
  // el último idioma elegido antes de "olvidarlo".
  useEffect(() => {
    if (!preferences) return;
    if (preferences.language) {
      void i18n.changeLanguage(preferences.language);
    } else {
      localStorage.removeItem(I18NEXT_LNG_STORAGE_KEY);
      void i18n.changeLanguage(detectBrowserLanguage());
    }
  }, [preferences]);

  return (
    <div className="min-h-screen">
      <header className="border-b">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <span className="flex shrink-0 items-center gap-2.5">
            <img src="/brand/logo.png" alt="" className="size-7" />
            <span className="bg-gradient-to-r from-chart-1 to-chart-2 bg-clip-text text-lg font-semibold tracking-tight text-transparent whitespace-nowrap">
              {t("app.name")}
            </span>
          </span>

          {/* Escritorio (>= lg): navegación y cuenta en línea. */}
          <nav className="hidden items-center gap-1 lg:flex">
            {NAV_ITEMS.map(({ to, labelKey, icon: Icon }) => (
              <NavLink key={to} to={to} className={navLinkClass}>
                <Icon className="size-4" />
                {t(labelKey)}
              </NavLink>
            ))}
          </nav>
          <div className="hidden items-center gap-3 text-sm lg:flex">
            {me?.email && <span className="text-muted-foreground">{me.email}</span>}
            <ThemeToggle />
            <NavLink
              to="/preferences"
              aria-label={t("nav.preferences")}
              title={t("nav.preferences")}
              className={({ isActive }) =>
                cn(buttonVariants({ variant: "outline", size: "sm" }), isActive && "bg-muted")
              }
            >
              <Settings className="size-4" />
            </NavLink>
            <Button
              variant="outline"
              size="sm"
              onClick={() => signOut.mutate()}
              disabled={signOut.isPending}
            >
              {t("auth.signOut")}
            </Button>
          </div>

          {/* Móvil y tablet (< lg): todo dentro de un único menú. */}
          <Popover open={menuOpen} onOpenChange={setMenuOpen}>
            <PopoverTrigger
              render={<Button variant="outline" size="icon-sm" className="lg:hidden" />}
              aria-label={t("nav.openMenu")}
            >
              <Menu className="size-4" />
            </PopoverTrigger>
            <PopoverContent align="end" className="w-64">
              <nav className="flex flex-col gap-1">
                {NAV_ITEMS.map(({ to, labelKey, icon: Icon }) => (
                  <NavLink
                    key={to}
                    to={to}
                    className={navLinkClass}
                    onClick={() => setMenuOpen(false)}
                  >
                    <Icon className="size-4" />
                    {t(labelKey)}
                  </NavLink>
                ))}
              </nav>
              <div className="border-t pt-2">
                {me?.email && (
                  <p className="truncate px-3 pb-1 text-xs text-muted-foreground">{me.email}</p>
                )}
                <ThemeToggle className="w-full px-3 py-1.5" />
                <NavLink
                  to="/preferences"
                  className={navLinkClass}
                  onClick={() => setMenuOpen(false)}
                >
                  <Settings className="size-4" />
                  {t("nav.preferences")}
                </NavLink>
                <Button
                  variant="ghost"
                  className="w-full justify-start px-3 text-sm font-normal text-muted-foreground hover:text-foreground"
                  onClick={() => {
                    setMenuOpen(false);
                    signOut.mutate();
                  }}
                  disabled={signOut.isPending}
                >
                  {t("auth.signOut")}
                </Button>
              </div>
            </PopoverContent>
          </Popover>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
