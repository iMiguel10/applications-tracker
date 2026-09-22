import { useTranslation } from "react-i18next";
import { Outlet } from "react-router-dom";

import { Button } from "@/shared/components/ui/button";
import { useMe } from "@/features/auth/hooks/queries/useMe";
import { useSignOut } from "@/features/auth/hooks/mutations/useSignOut";

/** Marco de las páginas autenticadas: cabecera con el usuario y cierre de sesión. */
export function AppLayout() {
  const { t } = useTranslation();
  const { data: me } = useMe();
  const signOut = useSignOut();

  return (
    <div className="min-h-screen">
      <header className="border-b">
        <div className="mx-auto flex max-w-2xl items-center justify-between gap-4 p-4">
          <span className="font-semibold">{t("app.name")}</span>
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
      <Outlet />
    </div>
  );
}
