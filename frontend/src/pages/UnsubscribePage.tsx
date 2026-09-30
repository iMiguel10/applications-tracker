import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";

import { useDocumentTitle } from "@/shared/hooks/useDocumentTitle";
import { errorMessageKey } from "@/shared/lib/errors";
import { AuthLayout } from "@/shared/components/layout/AuthLayout";
import { Button } from "@/shared/components/ui/button";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { useUnsubscribe } from "@/features/notifications/hooks/mutations/useUnsubscribe";
import { useUnsubscribeLink } from "@/features/notifications/hooks/queries/useUnsubscribeLink";
import { TOGGLE_FOR_KIND } from "@/features/notifications/types/NotificationSettings";

/** Destino del enlace de baja de los emails de aviso (RF-85). Funciona sin sesión.
 * Abrir la página no da de baja: hay que confirmarlo con el botón, porque los
 * servidores de correo abren solos los enlaces para analizarlos. */
export function UnsubscribePage() {
  const { t } = useTranslation();
  useDocumentTitle(t("unsubscribe.title"));
  const token = useSearchParams()[0].get("token");
  const link = useUnsubscribeLink(token);
  const unsubscribe = useUnsubscribe();

  const kind = unsubscribe.data?.kind ?? link.data?.kind;
  const notification = kind ? t(`notifications.${TOGGLE_FOR_KIND[kind]}.label`) : "";

  let body;
  if (!token) {
    body = <p role="alert" className="text-sm">{t("errors.invalid_unsubscribe_token")}</p>;
  } else if (link.isLoading) {
    body = <Skeleton className="h-16 w-full" />;
  } else if (link.isError || unsubscribe.isError) {
    body = (
      <p role="alert" className="text-sm">
        {t(errorMessageKey(link.error ?? unsubscribe.error))}
      </p>
    );
  } else if (unsubscribe.isSuccess) {
    body = (
      <p role="status" className="text-sm leading-relaxed">
        {t("unsubscribe.done", { notification })}
      </p>
    );
  } else {
    body = (
      <>
        <p className="text-sm leading-relaxed">{t("unsubscribe.question", { notification })}</p>
        <Button
          onClick={() => unsubscribe.mutate(token)}
          disabled={unsubscribe.isPending}
          className="w-full"
        >
          {t("unsubscribe.confirm")}
        </Button>
      </>
    );
  }

  return (
    <AuthLayout
      title={t("unsubscribe.title")}
      subtitle={t("unsubscribe.subtitle")}
      footer={
        <p className="text-sm text-muted-foreground">
          <Link
            to="/preferences"
            className="font-medium text-primary underline-offset-4 hover:underline"
          >
            {t("unsubscribe.toPreferences")}
          </Link>
        </p>
      }
    >
      <div className="grid gap-4">{body}</div>
    </AuthLayout>
  );
}
