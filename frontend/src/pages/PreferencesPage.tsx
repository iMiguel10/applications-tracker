import { useState } from "react";
import { Trash2 } from "lucide-react";
import { Trans, useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { Button } from "@/shared/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { DeleteAccountDialog } from "@/features/auth/components/DeleteAccountDialog";
import { PreferencesForm } from "@/features/auth/components/PreferencesForm";
import { useMe } from "@/features/auth/hooks/queries/useMe";
import { usePreferences } from "@/features/auth/hooks/queries/usePreferences";

export function PreferencesPage() {
  const { t } = useTranslation();
  const { data, isLoading, isError } = usePreferences();
  const { data: me } = useMe();
  const [deleteOpen, setDeleteOpen] = useState(false);

  return (
    <div className="grid gap-6">
      <h1 className="text-2xl font-semibold">{t("preferences.title")}</h1>

      {isLoading && <p className="text-muted-foreground">{t("common.loading")}</p>}
      {isError && <p className="text-destructive">{t("errors.generic")}</p>}
      {data && <PreferencesForm preferences={data} />}

      {me?.email && (
        <>
          <Card className="mt-6 max-w-md ring-destructive/25">
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
          <DeleteAccountDialog email={me.email} open={deleteOpen} onOpenChange={setDeleteOpen} />
        </>
      )}
    </div>
  );
}
