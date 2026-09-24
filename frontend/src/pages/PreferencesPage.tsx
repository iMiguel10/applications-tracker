import { useState } from "react";
import { Trash2 } from "lucide-react";
import { Trans, useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { useDocumentTitle } from "@/shared/hooks/useDocumentTitle";
import { Button } from "@/shared/components/ui/button";
import { ErrorState } from "@/shared/components/common/ErrorState";
import { ListSkeleton } from "@/shared/components/common/Skeletons";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { ChangePasswordCard } from "@/features/auth/components/ChangePasswordCard";
import { DeleteAccountDialog } from "@/features/auth/components/DeleteAccountDialog";
import { PreferencesForm } from "@/features/auth/components/PreferencesForm";
import { useMe } from "@/features/auth/hooks/queries/useMe";
import { usePreferences } from "@/features/auth/hooks/queries/usePreferences";

export function PreferencesPage() {
  const { t } = useTranslation();
  useDocumentTitle(t("preferences.title"));
  const { data, isLoading, isError, isFetching, refetch } = usePreferences();
  const { data: me } = useMe();
  const [deleteOpen, setDeleteOpen] = useState(false);

  return (
    <div className="grid gap-6">
      <h1 className="text-2xl font-semibold">{t("preferences.title")}</h1>

      {/* Ajustes a la izquierda y acciones de cuenta a la derecha, como el resto de
          páginas: ocupan el ancho completo en vez de una columna estrecha. */}
      <div className="grid items-start gap-6 lg:grid-cols-2">
        <div>
          {isLoading && <ListSkeleton rows={3} />}
          {isError && <ErrorState onRetry={() => refetch()} retrying={isFetching} />}
          {data && (
            <Card>
              <CardContent>
                <PreferencesForm preferences={data} />
              </CardContent>
            </Card>
          )}
        </div>

        {me?.email && (
          <div className="grid gap-6">
            <ChangePasswordCard email={me.email} />
            <Card className="ring-destructive/25">
              <CardHeader>
                <CardTitle>{t("account.delete.title")}</CardTitle>
                <CardDescription>
                  <Trans
                    i18nKey="account.delete.description"
                    components={{
                      link: (
                        <Link
                          to="/applications"
                          className="font-medium text-foreground underline underline-offset-4"
                        />
                      ),
                    }}
                  />
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button
                  variant="outline"
                  className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                  onClick={() => setDeleteOpen(true)}
                >
                  <Trash2 />
                  {t("account.delete.openButton")}
                </Button>
              </CardContent>
            </Card>
          </div>
        )}
      </div>

      {me?.email && (
        <DeleteAccountDialog email={me.email} open={deleteOpen} onOpenChange={setDeleteOpen} />
      )}
    </div>
  );
}
