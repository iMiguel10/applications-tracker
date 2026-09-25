import { useState } from "react";
import { MailCheck } from "lucide-react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { errorMessageKey, errorMessageParams } from "@/shared/lib/errors";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { useMeta } from "@/features/meta/hooks/queries/useMeta";
import { useEmailVerified } from "../hooks/queries/useEmailVerified";
import { useSendVerificationEmail } from "../hooks/mutations/useSendVerificationEmail";

/** Estado de verificación del email en Preferencias (RF-05): siempre visible, a
 * diferencia del aviso de la barra, que solo aparece mientras falta verificarlo. */
export function EmailVerificationCard({ email }: { email: string }) {
  const { t } = useTranslation();
  const { data: meta } = useMeta();
  const { data: verified, isLoading } = useEmailVerified();
  const resend = useSendVerificationEmail();
  const [resent, setResent] = useState(false);

  const onResend = () =>
    resend.mutate(undefined, {
      onSuccess: (result) => {
        if (result === "ok") setResent(true);
        else if (result === "error") toast.error(t("auth.errors.generic"));
      },
      onError: (error) => toast.error(t(errorMessageKey(error), errorMessageParams(error))),
    });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2">
          {t("account.email.title")}
          {isLoading ? (
            <Skeleton className="h-5 w-20" />
          ) : verified ? (
            <Badge variant="success">{t("account.email.verified")}</Badge>
          ) : (
            <Badge variant="outline">{t("account.email.unverified")}</Badge>
          )}
        </CardTitle>
        <CardDescription className="break-all">{email}</CardDescription>
      </CardHeader>
      {verified === false && (
        <CardContent className="grid gap-3">
          {meta?.email_enabled === false ? (
            <p className="text-sm text-muted-foreground">{t("account.email.unavailable")}</p>
          ) : resent ? (
            <p role="status" className="text-sm leading-relaxed">
              {t("auth.verifyEmail.bannerResent", { email })}
            </p>
          ) : (
            <>
              <p className="text-sm text-muted-foreground">{t("account.email.pending")}</p>
              <Button
                variant="outline"
                className="w-fit"
                onClick={onResend}
                disabled={resend.isPending}
              >
                <MailCheck />
                {t("auth.verifyEmail.resend")}
              </Button>
            </>
          )}
        </CardContent>
      )}
    </Card>
  );
}
