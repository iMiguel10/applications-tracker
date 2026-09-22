import { useTranslation } from "react-i18next";
import { NavLink, Outlet } from "react-router-dom";

import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/components/ui/button";
import { NAV_ITEMS } from "@/shared/config/navigation";
import { useMe } from "@/features/auth/hooks/queries/useMe";
import { useSignOut } from "@/features/auth/hooks/mutations/useSignOut";

/** Marco de las páginas autenticadas: navegación, usuario y cierre de sesión. */
export function AppLayout() {
  const { t } = useTranslation();
  const { data: me } = useMe();
  const signOut = useSignOut();

  return (
    <div className="min-h-screen">
      <header className="border-b">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-3">
          <div className="flex items-center gap-6">
            <span className="font-semibold">{t("app.name")}</span>
            <nav className="flex gap-1">
              {NAV_ITEMS.map(({ to, labelKey, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-2 rounded-md px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted hover:text-foreground",
                      isActive && "bg-muted font-medium text-foreground",
                    )
                  }
                >
                  <Icon className="size-4" />
                  {t(labelKey)}
                </NavLink>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-3 text-sm">
            {me?.email && <span className="text-muted-foreground">{me.email}</span>}
            <Button
              variant="outline"
              size="sm"
              onClick={() => signOut.mutate()}
              disabled={signOut.isPending}
            >
              {t("auth.signOut")}
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
